import cv2
import numpy as np
import random
import math

WINDOW_NAME  = "Astro-Dev Game"
GAME_WIDTH   = 800
GAME_HEIGHT  = 800
CHAR_SCALE   = 200
GRAVITY      = 2
JUMP_FORCE   = -22
WALK_SPEED   = 5
GROUND_Y     = 720
MAX_PLANETS  = 4
MAX_ALIENS   = 2
PLANET_SIZE  = 80
EXPLODE_SIZE = 110
EXPLODE_DURATION = 20
ALIEN_DISPLAY_W  = 80

MIN_HAND_AREA        = 5000
HAND_ROI_START_RATIO = 0.35

SKIN_LOWER1 = np.array([0,   48, 80],  dtype=np.uint8)
SKIN_UPPER1 = np.array([20, 255, 255], dtype=np.uint8)
SKIN_LOWER2 = np.array([160, 48, 80],  dtype=np.uint8)
SKIN_UPPER2 = np.array([179, 255, 255], dtype=np.uint8)


def load_sprite(path, width=None, height=None, size=None):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Aset tidak ditemukan: {path}")
    if img.shape[2] == 3:
        alpha = np.ones((*img.shape[:2], 1), dtype=np.uint8) * 255
        img = np.concatenate([img, alpha], axis=2)
    if size is not None:
        img = cv2.resize(img, size)
    elif width is not None and height is not None:
        img = cv2.resize(img, (width, height))
    elif width is not None:
        h, w = img.shape[:2]
        new_h = int(h * (width / w))
        img = cv2.resize(img, (width, new_h))
    elif height is not None:
        h, w = img.shape[:2]
        new_w = int(w * (height / h))
        img = cv2.resize(img, (new_w, height))
    return img


def slice_planet_spritesheet(path, cols=3, rows=3, target_size=80):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Aset tidak ditemukan: {path}")
    if img.shape[2] == 3:
        alpha = np.ones((*img.shape[:2], 1), dtype=np.uint8) * 255
        img = np.concatenate([img, alpha], axis=2)
    cell_h = img.shape[0] // rows
    cell_w = img.shape[1] // cols
    sprites = []
    for r in range(rows):
        for c in range(cols):
            cell = img[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
            sprites.append(cv2.resize(cell, (target_size, target_size)))
    return sprites


def overlay_sprite(frame, sprite, x, y):
    sh, sw = sprite.shape[:2]
    fh, fw = frame.shape[:2]
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + sw, fw), min(y + sh, fh)
    sx1, sy1 = x1 - x, y1 - y
    sx2, sy2 = sx1 + (x2 - x1), sy1 + (y2 - y1)
    if x2 <= x1 or y2 <= y1:
        return frame
    sp_crop = sprite[sy1:sy2, sx1:sx2]
    fr_crop = frame[y1:y2, x1:x2]
    alpha   = sp_crop[:, :, 3:4].astype(np.float32) / 255.0
    fg      = sp_crop[:, :, :3].astype(np.float32)
    bg      = fr_crop.astype(np.float32)
    blended = (alpha * fg + (1 - alpha) * bg).astype(np.uint8)
    frame[y1:y2, x1:x2] = blended
    return frame


def manual_erode(binary_img, kernel_size=5):
    pad = kernel_size // 2
    padded = np.pad(binary_img, pad, mode='constant', constant_values=0)
    output = np.zeros_like(binary_img)
    for y in range(binary_img.shape[0]):
        for x in range(binary_img.shape[1]):
            roi = padded[y:y+kernel_size, x:x+kernel_size]
            if np.all(roi == 255):
                output[y, x] = 255
    return output

def manual_dilate(binary_img, kernel_size=5):
    pad = kernel_size // 2
    padded = np.pad(binary_img, pad, mode='constant', constant_values=0)
    output = np.zeros_like(binary_img)
    for y in range(binary_img.shape[0]):
        for x in range(binary_img.shape[1]):
            roi = padded[y:y+kernel_size, x:x+kernel_size]
            if np.any(roi == 255):
                output[y, x] = 255
    return output


def get_hand_mask(frame):
    h_frame = frame.shape[0]
    roi_y   = int(h_frame * HAND_ROI_START_RATIO)

    full_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    roi = frame[roi_y:, :]

    roi_blur = cv2.GaussianBlur(roi, (5, 5), 0)
    hsv = cv2.cvtColor(roi_blur, cv2.COLOR_BGR2HSV)

    H = hsv[:, :, 0]
    S = hsv[:, :, 1]
    V = hsv[:, :, 2]

    mask1 = (H >= 0)   & (H <= 20)  & (S >= 30) & (S <= 255) & (V >= 60) & (V <= 255)
    mask2 = (H >= 160) & (H <= 179) & (S >= 30) & (S <= 255) & (V >= 60) & (V <= 255)

    combined_mask = (mask1 | mask2).astype(np.uint8) * 255

    m_processed = manual_dilate(combined_mask, kernel_size=5)
    m_processed = manual_erode(m_processed, kernel_size=5)
    m_processed = manual_erode(m_processed, kernel_size=5)
    final_mask  = manual_dilate(m_processed, kernel_size=5)

    full_mask[roi_y:, :] = final_mask
    return full_mask, roi_y


def get_largest_contour_in_region(mask, x_min, x_max):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, best_area = None, 0
    for cnt in contours:
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        cx = int(M["m10"] / M["m00"])
        if x_min <= cx < x_max:
            area = cv2.contourArea(cnt)
            if area > MIN_HAND_AREA and area > best_area:
                best_area = area
                best      = cnt
    return best


def count_fingers(contour):
    if contour is None or len(contour) < 5:
        return 0
    if cv2.contourArea(contour) < MIN_HAND_AREA:
        return 0
    hull_idx = cv2.convexHull(contour, returnPoints=False)
    if hull_idx is None or len(hull_idx) < 3:
        return 0
    try:
        defects = cv2.convexityDefects(contour, hull_idx)
    except cv2.error:
        return 0
    if defects is None:
        return 0
    count = 0
    for i in range(defects.shape[0]):
        s, e, f, d = defects[i, 0]
        start = tuple(contour[s][0])
        end   = tuple(contour[e][0])
        far   = tuple(contour[f][0])
        a = np.linalg.norm(np.array(end)   - np.array(start))
        b = np.linalg.norm(np.array(far)   - np.array(start))
        c = np.linalg.norm(np.array(end)   - np.array(far))
        cos_angle = (b**2 + c**2 - a**2) / (2 * b * c + 1e-6)
        angle = np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))
        if angle < 90 and d > 10000:
            count += 1
    return min(count + 1, 5)


def check_collision(ax, ay, aw, ah, bx, by, bw, bh):
    return (ax < bx + bw and ax + aw > bx and
            ay < by + bh and ay + ah > by)


def load_background(path):
    bg = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if bg is None:
        raise FileNotFoundError(f"Background tidak ditemukan: {path}")
    if len(bg.shape) == 2:
        bg = cv2.cvtColor(bg, cv2.COLOR_GRAY2BGR)
    if bg.shape[2] == 4:
        alpha  = bg[:, :, 3:4].astype(np.float32) / 255.0
        white  = np.ones_like(bg[:, :, :3], dtype=np.float32) * 255
        bg_bgr = (alpha * bg[:, :, :3].astype(np.float32) + (1 - alpha) * white).astype(np.uint8)
    else:
        bg_bgr = bg[:, :, :3]
    return cv2.resize(bg_bgr, (GAME_WIDTH, GAME_HEIGHT))


class Planet:
    def __init__(self, sprite_list, explode_sprite):
        self.sprite_list    = sprite_list
        self.explode_sprite = cv2.resize(explode_sprite, (EXPLODE_SIZE, EXPLODE_SIZE))
        self.sprite_idx     = random.randint(0, len(sprite_list) - 1)
        self.x              = float(random.randint(0, GAME_WIDTH - PLANET_SIZE))
        self.y              = float(-PLANET_SIZE)
        self.speed          = random.uniform(2, 5)
        self.w              = PLANET_SIZE
        self.h              = PLANET_SIZE
        self.exploding      = False
        self.explode_timer  = 0
        self.dead           = False

    def update(self):
        if self.exploding:
            self.explode_timer += 1
            if self.explode_timer >= EXPLODE_DURATION:
                self.dead = True
        else:
            self.y += self.speed

    def draw(self, frame):
        if self.exploding:
            offset = (EXPLODE_SIZE - PLANET_SIZE) // 2
            overlay_sprite(frame, self.explode_sprite,
                           int(self.x) - offset, int(self.y) - offset)
        else:
            overlay_sprite(frame, self.sprite_list[self.sprite_idx],
                           int(self.x), int(self.y))

    def hit(self):
        self.exploding     = True
        self.explode_timer = 0


class Alien:
    def __init__(self, sprite, explode_sprite):
        self.sprite         = sprite
        self.w              = sprite.shape[1]
        self.h              = sprite.shape[0]
        self.explode_sprite = cv2.resize(explode_sprite, (self.w, self.h))
        self.x              = float(random.randint(0, GAME_WIDTH - self.w))
        self.y              = float(-self.h)
        self.speed          = random.uniform(1.5, 3)
        self.frame_count    = 0
        self.drift_offset   = random.uniform(0, math.pi * 2)
        self.exploding      = False
        self.explode_timer  = 0
        self.dead           = False

    def update(self):
        if self.exploding:
            self.explode_timer += 1
            if self.explode_timer >= EXPLODE_DURATION:
                self.dead = True
        else:
            self.y += self.speed
            self.frame_count += 1
            self.x += math.sin(self.frame_count * 0.05 + self.drift_offset) * 2
            self.x  = max(0, min(GAME_WIDTH - self.w, self.x))

    def draw(self, frame):
        if self.exploding:
            overlay_sprite(frame, self.explode_sprite, int(self.x), int(self.y))
        else:
            overlay_sprite(frame, self.sprite, int(self.x), int(self.y))

    def hit(self):
        self.exploding     = True
        self.explode_timer = 0


class FloatingText:
    def __init__(self, text, x, y, color=(0, 255, 100)):
        self.text     = text
        self.x        = float(x)
        self.y        = float(y)
        self.color    = color
        self.lifetime = 30
        self.age      = 0

    def update(self):
        self.age += 1
        self.y   -= 1.5

    def draw(self, frame):
        alpha_ratio = max(0.0, 1.0 - self.age / self.lifetime)
        overlay = frame.copy()
        cv2.putText(overlay, self.text, (int(self.x), int(self.y)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, self.color, 2)
        cv2.addWeighted(overlay, alpha_ratio, frame, 1.0 - alpha_ratio, 0, frame)

    @property
    def dead(self):
        return self.age >= self.lifetime

class GameState:
    def __init__(self, sprites, planet_sprites, alien_sprite,
                 explode_sprite, background):
        self.sprites        = sprites
        self.planet_sprites = planet_sprites
        self.alien_sprite   = alien_sprite
        self.explode_sprite = explode_sprite
        self.background     = background
        self.char_w         = self.sprites["stay"].shape[1]
        self.reset()

    def reset(self):
        char_h                    = self.sprites["stay"].shape[0]
        self.x                    = float(max(0, min(GAME_WIDTH // 2 - self.char_w // 2,
                                                      GAME_WIDTH - self.char_w)))
        self.y                    = float(GROUND_Y - char_h)
        self.vy                   = 0.0
        self.is_jumping           = False
        self.direction            = "stay"
        self.score                = 0
        self.hearts               = 5
        self.game_over            = False
        self.planets              = []
        self.aliens               = []
        self.float_texts          = []
        self.spawn_timer          = 0
        self.alien_timer          = 0
        self.spawn_interval       = 90
        self.alien_spawn_interval = random.randint(150, 200)

    def _char_height(self):
        return self.sprites["stay"].shape[0]

    def update(self, left_fingers, right_fingers):
        if self.game_over:
            return

        self.direction = "stay"
        if left_fingers == 1:
            self.x        += WALK_SPEED
            self.direction = "right"
        elif left_fingers == 2:
            self.x        -= WALK_SPEED
            self.direction = "left"

        self.x = max(0.0, min(self.x, float(GAME_WIDTH - self.char_w)))

        if right_fingers in (1, 2, 3) and not self.is_jumping:
            self.vy         = JUMP_FORCE * right_fingers
            self.is_jumping = True

        self.vy += GRAVITY
        self.y  += self.vy

        floor = GROUND_Y - self._char_height()
        if self.y >= floor:
            self.y          = float(floor)
            self.vy         = 0.0
            self.is_jumping = False

        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_interval and len(self.planets) < MAX_PLANETS:
            self.planets.append(Planet(self.planet_sprites, self.explode_sprite))
            self.spawn_timer    = 0
            self.spawn_interval = 90 + random.randint(-30, 30)

        self.alien_timer += 1
        if self.alien_timer >= self.alien_spawn_interval and len(self.aliens) < MAX_ALIENS:
            self.aliens.append(Alien(self.alien_sprite, self.explode_sprite))
            self.alien_timer          = 0
            self.alien_spawn_interval = random.randint(150, 200)

        for p in self.planets:      p.update()
        for a in self.aliens:       a.update()
        for ft in self.float_texts: ft.update()

        self.check_collisions()

        self.planets     = [p  for p  in self.planets     if not p.dead]
        self.aliens      = [a  for a  in self.aliens      if not a.dead]
        self.float_texts = [ft for ft in self.float_texts if not ft.dead]

        if self.hearts <= 0:
            self.hearts    = 0
            self.game_over = True

    def check_collisions(self):
        char_h = self._char_height()
        ax, ay = int(self.x), int(self.y)

        for p in self.planets:
            if p.exploding or p.dead:
                continue
            if p.y + p.h >= GROUND_Y:
                self.hearts -= 1
                p.dead = True
                continue
            if self.is_jumping and check_collision(ax, ay, self.char_w, char_h,
                                                   int(p.x), int(p.y), p.w, p.h):
                self.score += 1
                p.hit()
                self.vy = -8
                self.float_texts.append(
                    FloatingText("+1", int(p.x + p.w // 2), int(p.y), (0, 220, 255)))

        for a in self.aliens:
            if a.exploding or a.dead:
                continue
            if a.y + a.h >= GROUND_Y:
                self.hearts -= 1
                a.dead = True
                continue
            if self.is_jumping and check_collision(ax, ay, self.char_w, char_h,
                                                   int(a.x), int(a.y), a.w, a.h):
                self.score += 2
                a.hit()
                self.vy = -8
                self.float_texts.append(
                    FloatingText("+2", int(a.x + a.w // 2), int(a.y), (0, 80, 255)))

    def draw(self):
        frame = self.background.copy()

        for p in self.planets: p.draw(frame)
        for a in self.aliens:  a.draw(frame)
        overlay_sprite(frame, self.sprites[self.direction], int(self.x), int(self.y))
        for ft in self.float_texts: ft.draw(frame)

        for i in range(5):
            color = (0, 0, 220) if i < self.hearts else (100, 100, 100)
            cv2.circle(frame, (30 + i * 32, 30), 12, color, -1)
            cv2.circle(frame, (30 + i * 32, 30), 12, (200, 200, 200), 1)

        score_text = f"SCORE: {self.score}"
        (tw, _), _ = cv2.getTextSize(score_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.putText(frame, score_text, (GAME_WIDTH - tw - 15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 220, 50), 2)

        if self.game_over:
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (GAME_WIDTH, GAME_HEIGHT), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
            cx = GAME_WIDTH // 2

            go_text = "GAME OVER"
            (tw, _), _ = cv2.getTextSize(go_text, cv2.FONT_HERSHEY_DUPLEX, 2.5, 3)
            cv2.putText(frame, go_text, (cx - tw // 2, GAME_HEIGHT // 2 - 60),
                        cv2.FONT_HERSHEY_DUPLEX, 2.5, (0, 40, 255), 3)

            s_text = f"Skor Akhir: {self.score}"
            (tw2, _), _ = cv2.getTextSize(s_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 2)
            cv2.putText(frame, s_text, (cx - tw2 // 2, GAME_HEIGHT // 2 + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

            r_text = "Tekan R untuk Restart"
            (tw3, _), _ = cv2.getTextSize(r_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            cv2.putText(frame, r_text, (cx - tw3 // 2, GAME_HEIGHT // 2 + 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 200), 2)

        return frame


def build_combined_display(game_frame, cam_view, mask_bgr):
    panel_h      = GAME_HEIGHT
    cam_panel_h  = panel_h // 2
    mask_panel_h = panel_h - cam_panel_h
    cam_w        = cam_view.shape[1]

    cam_small  = cv2.resize(cam_view, (cam_w, cam_panel_h))
    mask_small = cv2.resize(mask_bgr, (cam_w, mask_panel_h))

    cv2.putText(cam_small,  "CAMERA",   (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(mask_small, "HSV MASK", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.line(cam_small, (0, cam_panel_h - 2), (cam_w, cam_panel_h - 2), (255, 255, 0), 3)

    right_panel = np.vstack([cam_small, mask_small])
    return np.hstack([game_frame, right_panel])


def main():
    print("=== Astro-Dev Game ===")
    print("Tangan Kiri : 1=jalan kanan | 2=jalan kiri | 0/5=diam")
    print("Tangan Kanan: 1/2/3=lompat  | 5=tidak lompat")
    print("Q=keluar | R=restart (saat game over)")

    welcome_img = cv2.imread("assets/welcome.png")
    if welcome_img is None:
        raise FileNotFoundError("Aset tidak ditemukan: assets/welcome.png")
    welcome_img = cv2.resize(welcome_img, (GAME_WIDTH, GAME_HEIGHT))

    background = load_background("assets/background.png")
    sprites = {
        "stay":  load_sprite("assets/dev-stay.png",  width=CHAR_SCALE),
        "right": load_sprite("assets/dev-right.png", width=CHAR_SCALE),
        "left":  load_sprite("assets/dev-left.png",  width=CHAR_SCALE),
    }
    planet_sprites = slice_planet_spritesheet("assets/planet.png", 3, 3, PLANET_SIZE)
    alien_sprite   = load_sprite("assets/alien.png", width=ALIEN_DISPLAY_W)
    explode_sprite = load_sprite("assets/explode.png", size=(EXPLODE_SIZE, EXPLODE_SIZE))

    try:
        import winsound
        winsound.PlaySound("assets/not-ok.wav",
                           winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Kamera tidak bisa dibuka!")

    state   = GameState(sprites, planet_sprites, alien_sprite, explode_sprite, background)
    welcome = True

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame   = cv2.flip(frame, 1)
        frame   = cv2.resize(frame, (640, 480))
        frame_w = frame.shape[1]
        frame_h = frame.shape[0]

        mask, roi_y = get_hand_mask(frame)

        cnt_left  = get_largest_contour_in_region(mask, 0,            frame_w // 2)
        cnt_right = get_largest_contour_in_region(mask, frame_w // 2, frame_w)
        left_fingers  = count_fingers(cnt_left)
        right_fingers = count_fingers(cnt_right)

        if welcome:
            game_frame = welcome_img.copy()
        else:
            state.update(left_fingers, right_fingers)
            game_frame = state.draw()

        cam_view = frame.copy()
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

        cv2.line(cam_view, (0, roi_y),          (frame_w, roi_y),      (0, 255, 255), 1)
        cv2.line(mask_bgr, (0, roi_y),          (frame_w, roi_y),      (0, 200, 200), 1)
        cv2.line(cam_view, (frame_w//2, roi_y), (frame_w//2, frame_h), (255, 255, 0), 1)
        cv2.line(mask_bgr, (frame_w//2, roi_y), (frame_w//2, frame_h), (200, 200, 0), 1)

        cv2.putText(cam_view, "HAND ZONE", (5, roi_y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        cv2.putText(cam_view, "KIRI",      (10, roi_y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)
        cv2.putText(cam_view, "KANAN",     (frame_w // 2 + 10, roi_y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1)

        if cnt_left is not None:
            x, y, w, h = cv2.boundingRect(cnt_left)
            cv2.rectangle(cam_view, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.drawContours(cam_view, [cnt_left], -1, (0, 200, 0), 1)
            cv2.putText(cam_view, f"KIRI: {left_fingers} jari",
                        (x, max(y - 8, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

        if cnt_right is not None:
            x, y, w, h = cv2.boundingRect(cnt_right)
            cv2.rectangle(cam_view, (x, y), (x+w, y+h), (255, 100, 0), 2)
            cv2.drawContours(cam_view, [cnt_right], -1, (200, 80, 0), 1)
            cv2.putText(cam_view, f"KANAN: {right_fingers} jari",
                        (x, max(y - 8, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 100, 0), 2)

        combined = build_combined_display(game_frame, cam_view, mask_bgr)
        cv2.imshow(WINDOW_NAME, combined)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if welcome and key == ord('d'):
            welcome = False
        if not welcome and key == ord('r') and state.game_over:
            state.reset()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()