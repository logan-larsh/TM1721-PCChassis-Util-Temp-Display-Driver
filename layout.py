import os
import json

# Segment mappings for the Titan Micro TM1721 layout on Chip 2 (Left and Right dynamic display)
# These lists are directly derived from the decompiled C# binary segment logic.

SMGL3 = {
    0: [(0, 1), (2, 1), (12, 1), (10, 1), (8, 1), (4, 1)],
    1: [(2, 1), (12, 1)],
    2: [(0, 1), (2, 1), (6, 1), (8, 1), (10, 1)],
    3: [(0, 1), (2, 1), (6, 1), (12, 1), (10, 1)],
    4: [(2, 1), (12, 1), (4, 1), (6, 1)],
    5: [(0, 1), (12, 1), (10, 1), (4, 1), (6, 1)],
    6: [(0, 1), (12, 1), (10, 1), (8, 1), (4, 1), (6, 1)],
    7: [(0, 1), (2, 1), (12, 1)],
    8: [(0, 1), (2, 1), (12, 1), (10, 1), (8, 1), (4, 1), (6, 1)],
    9: [(0, 1), (2, 1), (12, 1), (10, 1), (4, 1), (6, 1)]
}

SMGL2 = {
    0: [(12, 2), (4, 2), (2, 2), (6, 2), (0, 2), (10, 2)],
    1: [(4, 2), (2, 2)],
    2: [(12, 2), (4, 2), (8, 2), (0, 2), (6, 2)],
    3: [(12, 2), (4, 2), (8, 2), (2, 2), (6, 2)],
    4: [(4, 2), (2, 2), (10, 2), (8, 2)],
    5: [(12, 2), (2, 2), (6, 2), (10, 2), (8, 2)],
    6: [(12, 2), (2, 2), (6, 2), (0, 2), (10, 2), (8, 2)],
    7: [(12, 2), (4, 2), (2, 2)],
    8: [(12, 2), (4, 2), (2, 2), (6, 2), (0, 2), (10, 2), (8, 2)],
    9: [(12, 2), (4, 2), (2, 2), (6, 2), (10, 2), (8, 2)]
}

SMGL1 = {
    0: [(2, 4), (10, 4), (4, 4), (12, 4), (8, 4), (0, 4)],
    1: [(10, 4), (4, 4)],
    2: [(2, 4), (10, 4), (6, 4), (8, 4), (12, 4)],
    3: [(2, 4), (10, 4), (6, 4), (4, 4), (12, 4)],
    4: [(10, 4), (4, 4), (0, 4), (6, 4)],
    5: [(2, 4), (4, 4), (12, 4), (0, 4), (6, 4)],
    6: [(2, 4), (4, 4), (12, 4), (8, 4), (0, 4), (6, 4)],
    7: [(2, 4), (10, 4), (4, 4)],
    8: [(2, 4), (10, 4), (4, 4), (12, 4), (8, 4), (0, 4), (6, 4)],
    9: [(2, 4), (10, 4), (4, 4), (12, 4), (0, 4), (6, 4)]
}

SMGR3 = {
    0: [(10, 8), (0, 8), (6, 8), (8, 8), (4, 8), (12, 8)],
    1: [(0, 8), (6, 8)],
    2: [(10, 8), (0, 8), (2, 8), (4, 8), (8, 8)],
    3: [(10, 8), (0, 8), (2, 8), (6, 8), (8, 8)],
    4: [(0, 8), (6, 8), (12, 8), (2, 8)],
    5: [(10, 8), (6, 8), (8, 8), (12, 8), (2, 8)],
    6: [(10, 8), (6, 8), (8, 8), (4, 8), (12, 8), (2, 8)],
    7: [(10, 8), (0, 8), (6, 8)],
    8: [(10, 8), (0, 8), (6, 8), (8, 8), (4, 8), (12, 8), (2, 8)],
    9: [(10, 8), (0, 8), (6, 8), (8, 8), (12, 8), (2, 8)]
}

SMGR2 = {
    0: [(4, 16), (2, 16), (12, 16), (8, 16), (10, 16), (0, 16)],
    1: [(2, 16), (12, 16)],
    2: [(4, 16), (2, 16), (6, 16), (10, 16), (8, 16)],
    3: [(4, 16), (2, 16), (6, 16), (12, 16), (8, 16)],
    4: [(2, 16), (12, 16), (0, 16), (6, 16)],
    5: [(4, 16), (12, 16), (8, 16), (0, 16), (6, 16)],
    6: [(4, 16), (12, 16), (8, 16), (10, 16), (0, 16), (6, 16)],
    7: [(4, 16), (2, 16), (12, 16)],
    8: [(4, 16), (2, 16), (12, 16), (8, 16), (10, 16), (0, 16), (6, 16)],
    9: [(4, 16), (2, 16), (12, 16), (8, 16), (0, 16), (6, 16)]
}

SMGR1 = {
    0: [(8, 32), (10, 32), (2, 32), (4, 32), (0, 32), (12, 32)],
    1: [(10, 32), (2, 32)],
    2: [(8, 32), (10, 32), (6, 32), (0, 32), (4, 32)],
    3: [(8, 32), (10, 32), (6, 32), (2, 32), (4, 32)],
    4: [(10, 32), (2, 32), (12, 32), (6, 32)],
    5: [(8, 32), (2, 32), (4, 32), (12, 32), (6, 32)],
    6: [(8, 32), (2, 32), (4, 32), (0, 32), (12, 32), (6, 32)],
    7: [(8, 32), (10, 32), (2, 32)],
    8: [(8, 32), (10, 32), (2, 32), (4, 32), (0, 32), (12, 32), (6, 32)],
    9: [(8, 32), (10, 32), (2, 32), (4, 32), (12, 32), (6, 32)]
}

def TM1721_CHAR(digit):
    # Mapping table for digits 0-9, space/blank (10), empty (11), and hyphen/error (14)
    table = {
        0: 95,   # 0x5F
        1: 80,   # 0x50
        2: 61,   # 0x3D
        3: 121,  # 0x79
        4: 114,  # 0x72
        5: 107,  # 0x6B
        6: 111,  # 0x6F
        7: 81,   # 0x51
        8: 127,  # 0x7F
        9: 123,  # 0x7B
        10: 128, # 0x80 (blank/space)
        11: 0,   # empty
        14: 47   # 0x2F (hyphen)
    }
    return table.get(digit, 0)

def nibble_swap(val):
    return ((val & 0x0F) << 4) | ((val & 0xF0) >> 4)

def to_bcd(val, digits_count=3, blank_leading=True):
    # Converts a value into list of BCD digits with leading zero blanking (maps to 10)
    digits = []
    temp = val
    for _ in range(digits_count):
        digits.append(temp % 10)
        temp //= 10
    digits.reverse()
    
    if blank_leading:
        for i in range(digits_count - 1):
            if digits[i] == 0:
                digits[i] = 10
            else:
                break
    return digits

def show1(cpu_temp, gpu_temp, cpu_util, fan_rpm):
    # Chips 1 LCD Buffer (16 segments)
    lcd_buf = [0] * 16
    
    # 1. Default icons / symbols
    lcd_buf[0] |= 8
    lcd_buf[1] |= 8
    lcd_buf[3] |= 8
    lcd_buf[4] |= 8
    lcd_buf[6] |= 0x8D
    lcd_buf[8] |= 0x80
    lcd_buf[10] |= 0x80
    
    # 2. Get BCD digits
    f_digits = to_bcd(fan_rpm, 4, blank_leading=True)
    u_digits = to_bcd(cpu_util, 3, blank_leading=True)
    g_digits = to_bcd(gpu_temp, 3, blank_leading=True)
    c_digits = to_bcd(cpu_temp, 3, blank_leading=True)
    
    # 3. Map Fan RPM digits to lcd_buf
    lcd_buf[0] |= nibble_swap(TM1721_CHAR(f_digits[3]))
    lcd_buf[1] |= nibble_swap(TM1721_CHAR(f_digits[2]))
    lcd_buf[2] |= nibble_swap(TM1721_CHAR(f_digits[1]))
    lcd_buf[3] |= nibble_swap(TM1721_CHAR(f_digits[0]))
    
    # 4. Map CPU Utilization to lcd_buf
    lcd_buf[4] |= nibble_swap(TM1721_CHAR(u_digits[2]))
    lcd_buf[5] |= nibble_swap(TM1721_CHAR(u_digits[1]))
    if u_digits[0] != 10 and u_digits[0] > 0:
        lcd_buf[6] |= 2
        
    # 5. Map GPU Temp to lcd_buf (nibble splitting)
    g0_char = TM1721_CHAR(g_digits[2])
    lcd_buf[6] |= (g0_char & 0xF0)
    lcd_buf[7] |= (g0_char & 0x0F)
    
    g1_char = nibble_swap(TM1721_CHAR(g_digits[1]))
    lcd_buf[7] |= (g1_char & 0xF0)
    lcd_buf[8] |= (g1_char & 0x0F)
    
    if g_digits[0] != 10 and g_digits[0] > 0:
        lcd_buf[7] |= 128
        
    # 6. Map CPU Temp to lcd_buf (nibble splitting)
    c0_char = TM1721_CHAR(c_digits[2])
    lcd_buf[8] |= (c0_char & 0xF0)
    lcd_buf[9] |= (c0_char & 0x0F)
    
    c1_char = TM1721_CHAR(c_digits[1])
    lcd_buf[9] |= (c1_char & 0xF0)
    lcd_buf[10] |= (c1_char & 0x0F)

    
    c2_char = TM1721_CHAR(c_digits[0])
    lcd_buf[10] |= (c2_char & 0xF0)
    lcd_buf[11] |= (c2_char & 0x0F)
    
    if c_digits[0] != 10 and c_digits[0] > 0:
        lcd_buf[9] |= 128
        
    return lcd_buf

def apply_digit_segments(lcd_buf, digit, dict_map):
    # Utility function to set segments for a digit from the lookup dictionary
    if digit == 10: # blank
        return
    segments = dict_map.get(digit, [])
    for idx, bitmask in segments:
        lcd_buf[idx] |= bitmask

def show4(left_val, right_val, mode):
    # Chip 2 LCD Buffer (16 segments)
    lcd_buf = [0] * 16
    
    # 1. Write mode icons
    if mode == 0: # Celsius
        lcd_buf[1] |= 4
        lcd_buf[5] |= 2
        lcd_buf[11] |= 4
        lcd_buf[7] |= 2
    elif mode == 1: # Fahrenheit
        lcd_buf[1] |= 4
        lcd_buf[3] |= 2
        lcd_buf[11] |= 4
        lcd_buf[9] |= 2
    elif mode == 2: # Utilization %
        lcd_buf[1] |= 4
        lcd_buf[5] |= 4
        lcd_buf[3] |= 4
        lcd_buf[1] |= 2
        lcd_buf[11] |= 4
        lcd_buf[9] |= 4
        lcd_buf[7] |= 4
        lcd_buf[11] |= 2
        
    # 2. Convert values to BCD
    left_digits = to_bcd(left_val, 3, blank_leading=True)
    right_digits = to_bcd(right_val, 3, blank_leading=True)
    
    # 3. Apply left digits
    apply_digit_segments(lcd_buf, left_digits[0], SMGL3)
    apply_digit_segments(lcd_buf, left_digits[1], SMGL2)
    apply_digit_segments(lcd_buf, left_digits[2], SMGL1)
    
    # 4. Apply right digits
    apply_digit_segments(lcd_buf, right_digits[0], SMGR3)
    apply_digit_segments(lcd_buf, right_digits[1], SMGR2)
    apply_digit_segments(lcd_buf, right_digits[2], SMGR1)
    
    return lcd_buf

CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")
_calibrated_segments = None

def load_calibration():
    global _calibrated_segments
    if _calibrated_segments is not None:
        return _calibrated_segments
    
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r") as f:
                _calibrated_segments = json.load(f)
                return _calibrated_segments
        except Exception as e:
            print(f"Error loading calibration.json: {e}")
    return []

def show5(cpu_util, gpu_util, existing_buf):
    # Make a copy of existing_buf to avoid mutating the original
    buf = list(existing_buf)
    
    segments = load_calibration()
    if not segments:
        return buf
        
    half = len(segments) // 2
    left_segs = segments[:half]
    right_segs = segments[half:]
    
    # Calculate number of dots to light up
    left_dots = max(0, min(len(left_segs), int(round(cpu_util * len(left_segs) / 100.0))))
    right_dots = max(0, min(len(right_segs), int(round(gpu_util * len(right_segs) / 100.0))))
    
    # Light up left dots
    for i in range(left_dots):
        seg = left_segs[i]
        grid = seg["grid"]
        mask = seg["mask"]
        buf[grid] |= mask
        
    # Light up right dots
    for i in range(right_dots):
        seg = right_segs[i]
        grid = seg["grid"]
        mask = seg["mask"]
        buf[grid] |= mask
        
    return buf

