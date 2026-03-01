import time
time.sleep(2)
from machine import Pin, SoftI2C
import onewire
import ds18x20
import ssd1306
import network
import socket
import json
import urequests
from config import NETWORKS, API_URL
import ntptime

wifi = network.WLAN(network.STA_IF)
wifi.active(False)  # najpierw wyłącz
time.sleep(1)
wifi.active(True)   # potem włącz
time.sleep(1)

connected = False
for ssid, password in NETWORKS:
    print("Próbuję:", ssid)
    wifi.disconnect()
    time.sleep(0.5)
    wifi.connect(ssid, password)
    for _ in range(20):
        if wifi.isconnected():
            connected = True
            break
        time.sleep(0.5)
    if connected:
        print("Połączono z:", ssid)
        break

if connected:
    ip = wifi.ifconfig()[0]
    print("IP:", ip)
    try:
        ntptime.settime()
    except:
        print("NTP failed")
else:
    ip = "brak WiFi"
    print("Brak WiFi - nie wysyłam danych")

i2c = SoftI2C(scl=Pin(22), sda=Pin(23))
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

ds_sensor = ds18x20.DS18X20(onewire.OneWire(Pin(32)))
roms = ds_sensor.scan()

oled.text("BOOT", 0, 0)
oled.show()

last_send_ok = False

def read_temperature():
    ds_sensor.convert_temp()
    time.sleep_ms(750)
    return ds_sensor.read_temp(roms[0])

def draw_degree(oled, x, y):
    oled.pixel(x,   y,   1)
    oled.pixel(x+1, y,   1)
    oled.pixel(x,   y+1, 1)
    oled.pixel(x+1, y+1, 1)

def show_temp(temp, send_ok=False):
    oled.fill(0)
    oled.text("Temperatura", 0, 0)
    temp_str = "{:.1f} ".format(temp)
    oled.text(temp_str, 0, 20)
    draw_degree(oled, len(temp_str) * 8 + 2, 20)
    oled.text("C", len(temp_str) * 8 + 6, 20)
    status = "Online" if send_ok else "Offline"
    oled.text(status, 0, 50)
    oled.show()
    
def send_temp(temp):
    try:
        t = time.localtime()
        hour = (t[3] + 1) % 24
        timestamp = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            t[0], t[1], t[2], hour, t[4], t[5]
        )
        data = json.dumps({
            "temperature": temp,
            "timestamp": timestamp
        })
        print("Wysyłam:", data)  # ← dodaj
        urequests.post(
            API_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        print("Wysłano OK")  # ← dodaj
        return True
    except Exception as e:
        print("Błąd wysyłania:", e)
        return False

server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('', 80))
server.listen(5)
server.setblocking(False)
print("Serwer działa!")

last_read = 0
temp = read_temperature()

while True:
    if time.ticks_diff(time.ticks_ms(), last_read) > 60000:
        temp = read_temperature()
        send_ok = send_temp(temp)
        show_temp(temp, send_ok)
        last_read = time.ticks_ms()

    try:
        conn, addr = server.accept()
        request = conn.recv(1024).decode()

        if "GET /temperature" in request:
            body = json.dumps({"temperature": temp, "unit": "C"})
            response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\n\r\n" + body
        else:
            response = "HTTP/1.1 404 Not Found\r\n\r\n"

        conn.send(response)
        conn.close()
    except:
        pass
