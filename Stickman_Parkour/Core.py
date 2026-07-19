import json
import base64
from pathlib import Path
import sys
import os
import pygame
import random

pygame.init()
pygame.mixer.init()

# --- MONITOR O'LCHAMINI ANIQLASH VA EKRANNI YARATISH ---
pygame.display.init()
monitors = pygame.display.get_desktop_sizes()
if monitors:
    monitor_w, monitor_h = monitors[0]
else:
    monitor_w, monitor_h = 1000, 700

# Haqiqiy oyna monitor o'lchamida ochiladi
screen = pygame.display.set_mode((monitor_w, monitor_h))
pygame.display.set_caption("Stickman Parkour")

# --- VIRTUAL O'YIN MAYDONI (1000x700) ---
GAME_W = 1000
GAME_H = 700
game_surface = pygame.Surface((GAME_W, GAME_H))

# O'yin maydonini monitor markaziga joylashtirish koordinatalari
render_x = (monitor_w - GAME_W) // 2
render_y = (monitor_h - GAME_H) // 2

clock = pygame.time.Clock()
font = pygame.font.SysFont("Sans-serif", 24)

dialogs = {}
configs = {}
received = False
gameStarted = False

white = (255, 255, 255)
yellow = (255, 255, 0)
black = (0, 0, 0)
green = (0, 255, 0) 
red = (255, 0, 0)
blue = (0, 0, 255)

# Menu boshlang'ich holati
menu_selection = 0 

y_velocity = 0       
is_grounded = False  
platforms = []    
triggers = [] 
walls = []
created = False
x = 12
walls1 = []
room = 1
key = pygame.key.get_pressed()

text_state = {
    "displayed_text": "",
    "char_index": 0,
    "is_finished": False
}

player = None
spawned = False
minSpeed = 5 
maxSpeed = 12

# --- SPRITE VA ANIMATSIYA TIZIMI ---
sprite_sheet = None
sprite_idle = None
sprite_walk1 = None
sprite_walk2 = None
sprite_jump = None
sprite_walkNjump = None
walk_cycle = []
walk_index = 0.0
facing_right = True
bg_cache = {}
current_music = None

# --- OVOZ EFFEKTLARI O'ZGARUVCHILARI ---
sound_click = None      # choose_sound.wav uchun
sound_gaster = None     # choose_sound_alt.wav uchun

def play_bg_music(music_file):
    music_file = 'mus/'+music_file
    global current_music
    if current_music != music_file:
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.play(-1)
            current_music = music_file
        except Exception as e:
            print(f"Musiqa yuklashda xatolik: {e}")

def get_image(sheet, frame_x, frame_y, width, height, scale_size, colorkey):
    image = pygame.Surface((width, height), pygame.SRCALPHA).convert_alpha()
    image.blit(sheet, (0, 0), (frame_x * width, frame_y * height, width, height))
    image = pygame.transform.scale(image, scale_size)
    if colorkey is not None:
        image.set_colorkey(colorkey)
    return image

def load_assets():
    global sprite_sheet, sprite_idle, sprite_walk1, sprite_walk2, sprite_jump, sprite_walkNjump, walk_cycle, bg_cache
    global sound_click, sound_gaster
    sprite_size = (50, 80)
    frame_w, frame_h = 125, 125 
    
    # 1. Sprite elementlarini yuklash
    try:
        sprite_sheet = pygame.image.load("sprite/stickman/stickman.png").convert_alpha()
        sprite_idle = get_image(sprite_sheet, 0, 0, frame_w, frame_h, sprite_size, None)
        sprite_walk1 = get_image(sprite_sheet, 4, 1, frame_w, frame_h, sprite_size, None)
        sprite_walk2 = get_image(sprite_sheet, 4, 3, frame_w, frame_h, sprite_size, None)
        sprite_jump = get_image(sprite_sheet, 4, 3, frame_w, frame_h, sprite_size, None)
        sprite_walkNjump = get_image(sprite_sheet, 4, 3, frame_w, frame_h, sprite_size, None)
        walk_cycle = [sprite_walk1, sprite_idle, sprite_walk2, sprite_idle]
    except Exception as error:
        print(f"Sprite yuklashda xatolik: {error}")
        sprite_idle = pygame.Surface(sprite_size); sprite_idle.fill(green)
        sprite_walk1 = pygame.Surface(sprite_size); sprite_walk1.fill((0, 200, 100))
        sprite_walk2 = pygame.Surface(sprite_size); sprite_walk2.fill((0, 200, 150))
        sprite_jump = pygame.Surface(sprite_size); sprite_jump.fill(blue)
        sprite_walkNjump = pygame.Surface(sprite_size); sprite_walkNjump.fill(yellow)
        walk_cycle = [sprite_walk1, sprite_idle, sprite_walk2, sprite_idle]

    # 2. Ovoz fayllarini yuklash va ovoz balandligini sozlash
    try:
        sound_click = pygame.mixer.Sound("sounds/choose_sound.mp3")
        sound_gaster = pygame.mixer.Sound("sounds/choose_sound_alt.mp3")
        
        sound_click.set_volume(0.5)
        sound_gaster.set_volume(0.15)  # Pasxalka effekti sirli chiqishi uchun past ovoz (15%)
    except Exception as sound_error:
        print(f"Ovoz fayllarini yuklashda xatolik: {sound_error}")

def get_background(level_id):
    global bg_cache
    if level_id not in bg_cache:
        bg_name = "bg_menu.png" if level_id == "menu" else f"bg_{int(level_id)}.png"
        bg_path = Path(f"sprite/backgrounds/{bg_name}")
        if bg_path.exists():
            img = pygame.image.load(str(bg_path)).convert()
            bg_cache[level_id] = pygame.transform.scale(img, (GAME_W, GAME_H))
        else:
            fallback = pygame.Surface((GAME_W, GAME_H))
            fallback.fill(black)
            bg_cache[level_id] = fallback
    return bg_cache[level_id]

def save_encrypted_configs():
    global configs
    try:
        raw_data = json.dumps(configs, ensure_ascii=False).encode('utf-8')
        encrypted_data = base64.b64encode(raw_data).decode('utf-8')
        with open(Path("Player_Info/configs.json"), 'w', encoding='utf-8') as file:
            file.write(encrypted_data)
    except Exception as ex:
        print("Shifrlashda xatolik:", ex)

def load_encrypted_configs():
    global configs
    configsName = Path("Player_Info/configs.json")
    if configsName.exists():
        with open(configsName, 'r', encoding='utf-8') as file:
            content = file.read().strip()
        try:
            decoded_bytes = base64.b64decode(content.encode('utf-8'))
            configs = json.loads(decoded_bytes.decode('utf-8'))
        except Exception:
            try:
                with open(configsName, 'r', encoding='utf-8') as f:
                    configs = json.load(f)
                save_encrypted_configs()
            except Exception:
                configs = {"Level": 1, "Language": "ru", "manualed": False, "key": 0, "chance": False}
    else:
        configs = {"Level": 1, "Language": "ru", "manualed": False, "key": 0, "chance": False}
        os.makedirs("Player_Info", exist_ok=True)
        save_encrypted_configs()

def choose(q, fit):
    game_surface.blit(get_background(configs["Level"]), (0, 0))
    texter(q, use_box=True, fit=fit, rgb=white)
    for event in pygame.event.get():
        if event.type == pygame.QUIT: break
    key = pygame.key.get_pressed()
    while not key[pygame.K_z]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: break
        key = pygame.key.get_pressed()
        if key[pygame.K_x]:
            return "no"
    return "yes"

def mainGame():
    global walls1, configs, dialogs, spawned, player, platforms, y_velocity, is_grounded, room, walls, key, received, x
    global walk_index, facing_right, gameStarted, current_music, sound_gaster, sound_click,created
    
    walls = []
    platforms = []
    walls1 = []
    
    game_surface.blit(get_background(configs["Level"]), (0, 0))
    
    if configs["Level"] == 1:
        if not configs["manualed"]:
            manual = choose(dialogs["dialog_005"], fit=30)
            if manual == 'no':
                configs['manualed'] = True
            else:
                game_surface.blit(get_background(configs["Level"]), (0, 0))
                texter(dialogs["dialog_006"], fit=30, use_box=True)
                while not key[pygame.K_z]:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT: return
                    key = pygame.key.get_pressed()
                game_surface.blit(get_background(configs["Level"]), (0, 0))
                texter(dialogs["dialog_006+1"], fit=30, use_box=True)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: return
                key = pygame.key.get_pressed()
                while not key[pygame.K_z]:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT: return
                    key = pygame.key.get_pressed()
                texter(dialogs["dialog_008"], fit=30, use_box=True)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: return
                key = pygame.key.get_pressed()
                while not key[pygame.K_z]:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT: return
                    key = pygame.key.get_pressed()
                configs['manualed'] = True
            save_encrypted_configs()

        if not spawned:
            player = pygame.Rect(275, GAME_H - 180, 20, 80)
            spawned = True

        if room == 1:
            createPlatform(200, 20, 200, GAME_H - 150, green)
            createPlatform(100, 20, 400, GAME_H - 270)
            createPlatform(200, 20, 600, GAME_H - 270)
            createPlatform(200, 20, 800, GAME_H - 320)
        elif room == 2:
            createPlatform(200, 20, 200, GAME_H - 150, green)
            createPlatform(100, 20, 400, GAME_H - 330)
            createPlatform(100, 20, 600, GAME_H - 400)
            createPlatform(200, 20, 800, GAME_H - 330)
            createWall(20, 150, 780, GAME_H - 480)
        elif room == 3:
            createPlatform(200, 20, 200, GAME_H - 150, green)
            createPlatform(100, 20, 500, GAME_H - 220)
            createWall(20, 100, 500, GAME_H - 320)
            createPlatform(100, 20, 700, GAME_H - 220)
            createWall(20, 100, 700, GAME_H - 320)
            createPlatform(100, 20, 900, GAME_H - 220)
            createWall(20, 100, 900, GAME_H - 320)
        elif room == 4:
            createPlatform(200, 20, 200, GAME_H - 150, green)
            createPlatform(100, 20, 500, GAME_H - 180)
            createWall1(20, 70, 500, GAME_H - 250, red)
            createPlatform(100, 20, 700, GAME_H - 180)
            createWall1(20, 70, 700, GAME_H - 250, red)
            createPlatform(100, 20, 900, GAME_H - 180)
            createWall1(20, 70, 900, GAME_H - 250, red)

    elif configs["Level"] == 2:
        if not spawned:
            player = pygame.Rect(50, GAME_H - 150, 20, 80)
            spawned = True
        if room == 1:
            createPlatform(150, 20, 30, GAME_H - 70, green)
            createPlatform(120, 20, 250, GAME_H - 180)
            createPlatform(120, 20, 500, GAME_H - 300)
            createWall1(20,100,600,GAME_H-400)
            createPlatform(200, 20, 750, GAME_H - 220)
        elif room == 2:
            createPlatform(150, 20, 30, GAME_H - 70, green)
            createPlatform(100, 20, 300, GAME_H - 250)
            createWall1(20, 100, 380, GAME_H - 350, red)
            createPlatform(100, 20, 550, GAME_H - 250)
            createWall1(20,100,650,GAME_H-350)
            createPlatform(150, 20, 760, GAME_H - 400)
        elif room == 3:
            createPlatform(150, 20, 30, GAME_H - 70, green)
            createPlatform(80, 20, 250, GAME_H - 200)
            createWall1(80,20,375,GAME_H-275,white)
            createPlatform(80, 20, 500, GAME_H - 350)
            createPlatform(200, 20, 800, GAME_H - 150)
        elif room == 4:
            createPlatform(150, 20, 30, GAME_H - 70, green)
            createPlatform(100, 20, 300, GAME_H - 280)
            createWall1(20, 100, 400, GAME_H - 380, red)
            createPlatform(150, 20, 550, GAME_H - 220)
            createPlatform(200, 20, 800, GAME_H - 350)

    elif configs["Level"] == 3:
        if not spawned:
            player = pygame.Rect(60, GAME_H - 220, 20, 80)
            spawned = True
        if room == 1:
            createPlatform(100, 20, 20, GAME_H - 140, green)
            createPlatform(80, 20, 250, GAME_H - 200)
            createWall1(80,20,400,GAME_H-200,white)
            createPlatform(80,20,530,GAME_H-200)
            createWall1(80,20,680,GAME_H-200,white)
            createPlatform(80,20,760,GAME_H-200)
            createWall1(80,20,940,GAME_H-200,white)
        elif room == 2:
            createPlatform(100, 20, 20, GAME_H - 140, green)
            createPlatform(90, 20, 300, GAME_H - 350)
            createWall1(20, 120, 450, GAME_H - 450)
            createPlatform(90, 20, 600, GAME_H - 200)
            createPlatform(150, 20, 850, GAME_H - 300)
        elif room == 3:
            createPlatform(100, 20, 20, GAME_H - 140, green)
            createPlatform(70, 20, 250, GAME_H - 180)
            createPlatform(70, 20, 500, GAME_H - 280)
            createWall1(30, 90, 600, GAME_H - 370, red)
            createPlatform(200, 20, 750, GAME_H - 150)
        elif room == 4:
            createPlatform(100, 20, 20, GAME_H - 140, green)
            createPlatform(100, 20, 300, GAME_H - 250)
            createWall1(40, 100, 500, GAME_H - 350, red)
            createPlatform(100, 20, 650, GAME_H - 180)
            createPlatform(200, 20, 800, GAME_H - 300)

    if configs["Level"] == 4:
        if not spawned:
            player = pygame.Rect(50, GAME_H - 150, 20, 80)
            spawned = True
        if room == 1:
            createPlatform(150, 20, 20, GAME_H - 100, green)
            createPlatform(100, 20, 300, GAME_H - 220)
            createPlatform(200, 20, 700, GAME_H - 300)
        elif room == 2:
            createPlatform(150, 20, 20, GAME_H - 100, green)
            createPlatform(90, 20, 300, GAME_H - 200)
            createWall1(25, 120, 450, GAME_H - 280, red)
            createPlatform(150, 20, 650, GAME_H - 350)
            createPlatform(150, 20, 850, GAME_H - 200)
        elif room == 3:
            createPlatform(150, 20, 20, GAME_H - 100, green)
            createPlatform(80, 20, 300, GAME_H - 300)
            createPlatform(80, 20, 550, GAME_H - 180)
            createPlatform(150, 20, 800, GAME_H - 280)
        elif room == 4:
            createPlatform(150, 20, 20, GAME_H - 100, green)
            createPlatform(100, 20, 250, GAME_H - 150)
            createPlatform(100, 20, 500, GAME_H - 250)
            if configs["key"] == 3:
                createPlatform(60, 20, 700, GAME_H - 380, yellow)
                createPlatform(60, 20, 820, GAME_H - 480, yellow)
                createPlatform(150, 20, 900, GAME_H - 580, green)
            else:
                createPlatform(150, 20, 850, GAME_H - 150)
                configs["Level"] = 4.1
    if configs["Level"] == 5:
        if not spawned:
            player = pygame.Rect(50, GAME_H - 150, 20, 80)
            spawned = True
        if room == 1:
            createPlatform(200,20,50,GAME_H-150)
            createPlatform(200,20,350,GAME_H-300)
            createWall1(20,100,440,GAME_H-400)
            createWall1(100,20,600,GAME_H-300, white)
            createPlatform(100,20,750, GAME_H-300)
            createPlatform(100,20,900, GAME_H-300)
        if room == 2:
            createPlatform(200,20,0,GAME_H-150)
            createPlatform(200,20,300,GAME_H-230)
            createWall1(100,10,400, GAME_H-330)
            createPlatform(200,20,650,GAME_H-230)
            createPlatform(150,20,850,GAME_H-350)
        if room == 3:
            createPlatform(200,20,100,GAME_H-150)
            if not created:
                created = True
                x = random.randint(1,100) % 2
            if x:
                createWall1(100,20,400,GAME_H-150)
            else:
                createPlatform(100,20,600,GAME_H-150)
            if x:
                createPlatform(100,20,600,GAME_H-150)
            else:
                createWall1(100,20,600,GAME_H-150)
            if x:
                createWall1(100,20,800,GAME_H-150)
            else:
                createPlatform(100,20,800,GAME_H-150)
            createPlatform(100,20,900,GAME_H-150)
    if configs["Level"] == 4.1:
        # Pasxalka darajasiga kelganda fon musiqasini butunlay o'chiramiz
        play_bg_music("noMusic.mp3")
        screen.fill(black)
        # Birinchi dialog qutisi chiqadi, gaster ovozi hali chalinmaydi
        texter(dialogs["dialog_013"], fit=40,use_box=True, speed=100)
        
        while not pygame.key.get_pressed()[pygame.K_z]:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or pygame.key.get_pressed()[pygame.K_x]: 
                    return 'Exit'
        
        # O'yinchi Z tugmasini bosib Reset qilganidan keyin Gaster ovozi eshitiladi
        if sound_gaster:
            sound_gaster.play()
            
        configs = {"Level":1, "Language":"ru", "key":0, "manualed":False}
        save_encrypted_configs()
        room = 1
        for event in pygame.event.get():
               key = pygame.key.get_pressed()
        return 'Menu'

    key = pygame.key.get_pressed()
    speed = minSpeed
    is_moving = False
    
    if key[pygame.K_x] or key[pygame.K_RSHIFT] or key[pygame.K_LSHIFT]:
        speed = maxSpeed

    # Kalit olish faqat Level 1, Room 1 da ishlashi uchun daraja ham tekshiriladi
    if (key[pygame.K_z] or key[pygame.K_KP_ENTER]):
        if configs["Level"] == 1 and received == False:
            if room == 1 and 400 < player.x < 500:
                configs["key"] += 1 
                # Kalit olinganda fon orqasiga qora quti chiziladi
                texter(dialogs["dialog_010"], fit=40, use_box=True, printPLayer=True)
                while not pygame.key.get_pressed()[pygame.K_z]:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT: return
                received = True
                save_encrypted_configs()
        elif configs["Level"] == 2 and not received:
            if room == 1 and 250 < player.x < 370:
                configs["key"]+=1
                received = True
                texter(dialogs["dialog_010"], fit=40, use_box=True, printPLayer=True)
                while not pygame.key.get_pressed()[pygame.K_z]:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT: return
                save_encrypted_configs()
        elif configs["Level"] == 3 and not received:
            if room == 1 and 250 < player.x < 330:
                configs["key"]+=1
                received = True
                texter(dialogs["dialog_010"], fit=40, use_box=True, printPLayer=True)
                while not pygame.key.get_pressed()[pygame.K_z]:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT: return
                save_encrypted_configs()
        elif configs["Level"] == 4 and not received:
            if room == 1 and 300 < player.x < 400:
                configs["choice"] = True
                received = True
                texter(dialogs["dialog_011"], fit=40, use_box=True, printPLayer=True)
                while not pygame.key.get_pressed()[pygame.K_z]:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT: return
                save_encrypted_configs()

    if key[pygame.K_RIGHT]:
        player.x += speed
        facing_right = True
        is_moving = True
        for plat in walls:
            if player.colliderect(plat): player.x -= speed
        for plat in walls1:
            if player.colliderect(plat): 
                if configs["Level"] == 5:
                    configs["Level"] = 4
                    room = 4
                    save_encrypted_configs()
                spawned = False
                
    if key[pygame.K_LEFT]:
        player.x -= speed
        facing_right = False
        is_moving = True
        for plat in walls:
            if player.colliderect(plat): player.x += speed
        for plat in walls1:
            if player.colliderect(plat): spawned = False

    if key[pygame.K_ESCAPE]:
        return 'Menu'
        
    if key[pygame.K_UP] and is_grounded:
        y_velocity = -12 
        is_grounded = False
        
    y_velocity += 0.6
    player.y += y_velocity

    is_grounded = False
    for plat in platforms:
        if player.colliderect(plat) and y_velocity > 0:
            player.bottom = plat.top
            y_velocity = 0
            is_grounded = True

    if room == 1 and player.x < 0:
        player.x = 0
    
    if player.y < -100:
        player.y = -100
        y_velocity = 0

    if player.y >= GAME_H:
        if configs["Level"] == 5:
            if room == 1: room = 4
            elif room == 2: room = 3
            elif room == 3: room = 2
            elif room == 4: room = 1
            configs["Level"] = 4
            created = False
            game_surface.blit(get_background(4),(0,0))
            save_encrypted_configs()        
        spawned = False

    if player.x >= GAME_W:
        if room < 4:
            room += 1
            player.x = 0
            received = False
        else:
            configs["Level"] += 1
            room = 1
            spawned = False
            game_surface.blit(get_background(configs["Level"]-1), (0, 0))
            texter(dialogs["dialog_009"], fit=40, x=GAME_W/2-250, y=GAME_H/2)
            while not pygame.key.get_pressed()[pygame.K_z]:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: return
            save_encrypted_configs()
    elif player.x <= -50 and room > 1:
        room -= 1
        player.x = GAME_W - 50
            
    # --- ANIMATSIYA SELEKTORI ---
    if not is_grounded:
        current_sprite = sprite_walkNjump if is_moving else sprite_jump
    else:
        if is_moving:
            walk_index += 0.15
            if walk_index >= len(walk_cycle): walk_index = 0
            current_sprite = walk_cycle[int(walk_index)]
        else:
            current_sprite = sprite_idle
            walk_index = 0

    if not facing_right:
        current_sprite = pygame.transform.flip(current_sprite, True, False)

    game_surface.blit(current_sprite, (player.x, player.y))

def mainmenu():
    global configs, dialogs, menu_selection, sound_click
    game_surface.blit(get_background("menu"), (0, 0))
    
    a = '* ' if menu_selection == 0 else ''
    c = yellow if menu_selection == 0 else white
    b = '* ' if menu_selection == 1 else ''
    d = yellow if menu_selection == 1 else white
    e = '* ' if menu_selection == 2 else ''
    f = yellow if menu_selection == 2 else white

    texter(a + dialogs.get("dialog_001", "Start"), 100, 500, 0, 30, c) 
    texter(b + dialogs.get("dialog_002", "English"), 100, 550, 0, 30, d)
    texter(e + dialogs.get("dialog_003", "Exit"), 100, 600, 0, 30, f)
    
    keyboard = pygame.key.get_pressed()
    if keyboard[pygame.K_DOWN]:
        sound_click.play()
        menu_selection = (menu_selection + 1) % 3
        pygame.time.wait(150) 
    elif keyboard[pygame.K_UP]:
        sound_click.play()
        menu_selection = (menu_selection - 1) % 3
        pygame.time.wait(150)
    elif keyboard[pygame.K_z]:
        sound_click.play()
            
        if menu_selection == 2: return 'Exit'
        elif menu_selection == 1:  
            if configs["Language"] == "ru": configs["Language"] = "en"
            elif configs["Language"] == "en": configs["Language"] = "uz"
            else: configs["Language"] = "ru"
            save_encrypted_configs()
            jsonLoad()
            pygame.time.wait(200)
        elif menu_selection == 0: return "StartGame"

def createPlatform(width1, height1, x, y, rgb=white):
    wall = pygame.Rect(x, y, width1, height1)
    pygame.draw.rect(game_surface, rgb, wall)
    platforms.append(wall) 
def createWall(width1, height1, x, y, rgb=white):
    wall = pygame.Rect(x, y, width1, height1)
    pygame.draw.rect(game_surface, rgb, wall)
    walls.append(wall)
def createWall1(width1, height1, x, y, rgb=red):
    wall = pygame.Rect(x, y, width1, height1)
    pygame.draw.rect(game_surface, rgb, wall)
    walls1.append(wall)

def jsonLoad():
    global configs, dialogs
    load_encrypted_configs()
    lang_path = Path(f"lang/{configs['Language']}_dialogs.json")
    if lang_path.exists():
        with open(lang_path, "r", encoding='utf-8') as file:
            dialogs = json.load(file)
    else:
        game_surface.fill(black)
        texter(configs["Language"]+"_dialogs.json file doesn't exist.", GAME_W/2-300, GAME_H/2, 25, 40, white)
        flip()
        pygame.time.delay(500)
        return "ERR" 

def texter(full_text, x=190, y=120, speed=50, fit=24, rgb=white, use_box=False, printPLayer=False):
    global font
    font = pygame.font.SysFont("Sans-serif", fit)
    global text_state
    
    # use_box mantiqi to'g'rilandi: matn chizilishidan oldin qora fon qutisi yaratiladi
    if use_box:
        pygame.draw.rect(game_surface, black, pygame.Rect(150, 100, 700, 200))
        pygame.draw.rect(game_surface, white, pygame.Rect(150, 100, 700, 200), 2) # Chiroyli oq ramka
        
    if speed > 0:
        while not text_state["is_finished"]:
            if text_state["char_index"] >= len(full_text): break
            if full_text[text_state["char_index"]] == "$":
                y += fit
                text_state["char_index"] += 2
                text_state["displayed_text"] = ""
            if full_text[text_state["char_index"]] == '#':
                pygame.time.delay(speed * 3)
                text_state["char_index"] += 1
            if not text_state["is_finished"]:
                text_state["displayed_text"] += full_text[text_state['char_index']]
                if printPLayer:
                    game_surface.blit(get_background(configs["Level"]), (0, 0))
                    if use_box:
                        pygame.draw.rect(game_surface, black, pygame.Rect(150, 100, 700, 200))
                        pygame.draw.rect(game_surface, white, pygame.Rect(150, 100, 700, 200), 2)
                    for p in platforms: pygame.draw.rect(game_surface, white, p)
                    if player: game_surface.blit(sprite_idle, (player.x, player.y))
                text_surface = font.render(text_state["displayed_text"], True, rgb)
                game_surface.blit(text_surface, (x, y))
                pygame.time.wait(speed)
                text_state["char_index"] += 1
                flip()
    else:
        text_surface = font.render(full_text, True, rgb)
        game_surface.blit(text_surface, (x, y))
    text_state = {"displayed_text": "", "char_index": 0, "is_finished": False}
    font = pygame.font.SysFont("Sans-serif", 24) 

def flip():
    screen.fill(black)
    screen.blit(game_surface, (render_x, render_y))
    pygame.display.flip()

running = True
if jsonLoad() == "ERR": running = False
load_assets()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

    if not gameStarted:
        play_bg_music("mainMenu.mp3")
        answ = mainmenu()
        if answ == 'StartGame': gameStarted = True
        elif answ == 'Exit': running = False
    else:
        play_bg_music("mainGame.mp3")
        answ = mainGame()
        if answ == 'Exit': running = False
        elif answ == 'Menu': 
            gameStarted = False
            current_music = ''

    flip()
    clock.tick(60)

pygame.mixer.music.stop()
pygame.quit()
sys.exit()