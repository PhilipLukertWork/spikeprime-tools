#!/usr/bin/env python3

import serial
import base64
import os
# import sys
import argparse
from tqdm import tqdm
import time
import json
import random
import string
import logging
from datetime import datetime

letters = string.ascii_letters + string.digits + '_'
def random_id(len = 4):
  return ''.join(random.choice(letters) for _ in range(4))

class RPC:
  def __init__(self, tty = '/dev/ttyACM0'):
    try:
      self.ser = serial.Serial(tty, 115200)
    except Exception as e:
      self.exitSerial(0)
    self.recv_buf = bytearray()

  def recv_message(self, timeout = 1):
    start_time = time.time()
    elapsed = 0
    while True:
      pos = self.recv_buf.find(b'\x0d')
      if pos >= 0:
        result = self.recv_buf[:pos]
        self.recv_buf = self.recv_buf[pos+1:]
        try:
          return json.loads(result.decode('utf-8'))
        except json.JSONDecodeError:
          logging.debug("Cannot parse JSON: %s" % result)
      try:
        c = self.ser.in_waiting
        if c == 0 and elapsed >= timeout:
          break
        self.ser.timeout = 1
        self.recv_buf += self.ser.read(c if c else 1)
      except Exception as e:
        self.exitSerial(1)
        
      elapsed = time.time() - start_time
    return None

  def send_message(self, name, params = {}):
    while True:
      if not self.recv_message(timeout=0):
        break
    id = random_id()
    msg = {'m':name, 'p': params, 'i': id}
    msg_string = json.dumps(msg)
    logging.debug('sending: %s' % msg_string)
    try:
      self.ser.write(msg_string.encode('utf-8'))
      self.ser.write(b'\x0D')
    except Exception as e:
      self.exitSerial(2)
    return self.recv_response(id)

  def send_empty(self, id):
    while True:
      if not self.recv_message(timeout=0):
        break
    msg = {'i': id, 'r': None}
    msg_string = json.dumps(msg)
    logging.debug('sending: %s' % msg_string)
    try:
      self.ser.write(msg_string.encode('utf-8'))
      self.ser.write(b'\x0D')
    except Exception as e:
      self.exitSerial(3)

  def recv_response(self, id):
    while True:
      m = self.recv_message()
      if not m is None and 'i' in m and m['i'] == id:
        logging.debug('response: %s' % m)
        if 'e' in m:
          error = json.loads(base64.b64decode(m['e']).decode('utf-8'))
          #raise ConnectionError(error)
          print(error)
          exit(0)
        return m['r']
      logging.debug('while waiting for response: %s' % m)

  def continued_reading(self, id):
    while True:
      m = self.recv_message()
      if m is None or not 'm' in m:  # keine Nachricht
        continue
      elif m['m'] in [0, 2, 4]:  # Gyroskop-Spam ignorieren
        continue
      elif m['m'] == 3 and 'p' in m and len(m['p']) == 2:  # Button
        ms = m['p'][1]
        if ms == 0:
          print(f"Schalter wurde gedrückt.")
        else:
          print(f"Schalter wurde nach {ms}ms losgelassen.")
      elif m['m'] == 12 and 'p' in m and len(m['p']) == 2:  # Program-Status
        running = m['p'][1]
        if not running and not m['p'][0] is None:
          print(f"Programm wurde beendet", m)
          break
      elif m['m'] == 'userProgram.print' and 'p' in m and 'value' in m['p']:  # Print
        try:
          print(base64.b64decode(m['p']['value']).decode('utf-8'), end="")
          self.send_empty(m['i'])  #response to not produce an error
        except:
          print("Error decoding print-json:", m['p']['value'])
      elif m['m'] == 'user_program_error' and 'p' in m and len(m['p']) == 5:  # Error
        try:
          print(base64.b64decode(m['p'][3]).decode('utf-8'))
          print(base64.b64decode(m['p'][4]).decode('utf-8'))
        except:
          print("Error decoding error-json:", m)
      else:
        print("Unknown message format:", m)

  def exitSerial(self, errorId, extraMessage = ""):
    try:
      if not self.ser is None:
        self.ser.close()
    except AttributeError:
      pass
    except:
      print("Fehler beim schließen der USB-Verbindung")
    if (errorId == -1):
      print("Fehler beim Lesen der Datei, die auf den Spike geladen werden soll. Rufe einen Betreuer")
      print(e)
    else:
      print(f"USB-Fehler({errorId}): Ziehe das Kabel heraus und stecke es nach 5s neu ein")
    exit(0)


# Program Methods
  def program_execute(self, n):
    self.send_message('program_execute', {'slotid': n})
    self.continued_reading(n)

  def program_terminate(self):
    return self.send_message('program_terminate')

  def get_storage_information(self):
    return self.send_message('get_storage_status')

  def start_write_program(self, name, size, slot, created, modified):
    meta = {'created': created, 'modified': modified, 'name': name, 'type': 'python', 'project_id': '50uN1ZaRpHj2'}
    return self.send_message('start_write_program', {'slotid':slot, 'size': size, 'meta': meta})

  def write_package(self, data, transferid):
    return self.send_message('write_package', {'data': str(base64.b64encode(data), 'utf-8'), 'transferid': transferid})

  def move_project(self, from_slot, to_slot):
    return self.send_message('move_project', {'old_slotid': from_slot, 'new_slotid': to_slot})

  def remove_project(self, from_slot):
    return self.send_message('remove_project', {'slotid': from_slot })

# Light Methods
  def display_set_pixel(self, x, y, brightness = 9):
    return self.send_message('scratch.display_set_pixel', { 'x':x, 'y': y, 'brightness': brightness})

  def display_clear(self):
    return self.send_message('scratch.display_clear')

  def display_image(self, image):
    return self.send_message('scratch.display_image', { 'image':image })

  def display_image_for(self, image, duration_ms):
    return self.send_message('scratch.display_image_for', { 'image':image, 'duration': duration_ms })

  def display_text(self, text):
    return self.send_message('scratch.display_text', {'text':text})

# Hub Methods
  def get_firmware_info(self):
    return self.send_message('get_hub_info')


if __name__ == "__main__":
  def handle_list():
    info = rpc.get_storage_information()
    storage = info['storage']
    slots = info['slots']
    print("%4s %-40s %6s %-20s %-12s %-10s" % ("Slot", "Decoded Name", "Size",  "Last Modified", "Project_id", "Type"))
    for i in range(20):
      if str(i) in slots:
        sl = slots[str(i)]
        modified = datetime.utcfromtimestamp(sl['modified']/1000).strftime('%Y-%m-%d %H:%M:%S')
        try:
          decoded_name = base64.b64decode(sl['name']).decode('utf-8')
        except:
          decoded_name = sl['name']
        try:
          project = sl['project_id']
        except:
          project = " "
        try:
          type = sl['type']
        except:
          type = " "
        try:
          size = sl['size']
        except:
          size = 0

        # print("%2s %-40s %-40s %5db %6s %-20s %-20s %-10s" % (i, sl['name'], decoded_name, sl['size'], sl['id'], modified, project, type))
        print("%4s %-40s %5db %-20s %-12s %-10s" % (i, decoded_name, size, modified, project, type))
    print(("Storage free %s%s of total %s%s" % (storage['free'], storage['unit'], storage['total'], storage['unit'])))
  
  def handle_fwinfo():
    info = rpc.get_firmware_info()
    fw = '.'.join(str(x) for x in info['firmware']['version'])
    rt = '.'.join(str(x) for x in info['runtime']['version'])
    print("Firmware version: %s; Runtime version: %s" % (fw, rt))
  
  def handle_upload():
    try:
      with open(args.file, "rb") as f:
        size = os.path.getsize(args.file)
        name = args.name if args.name else args.file
        now = int(time.time() * 1000)
        start = rpc.start_write_program(name, size, args.to_slot, now, now)
        bs = start['blocksize']
        id = start['transferid']
        with tqdm(total=size, unit='B', unit_scale=True) as pbar:
          b = f.read(bs)
          while b:
            rpc.write_package(b, id)
            pbar.update(len(b))
            b = f.read(bs)
        if not args.no_start:
          rpc.program_execute(args.to_slot)
    except IOError as e:
      rpc.exitSerial(-1, e);

  parser = argparse.ArgumentParser(description='Tools for Spike Hub RPC protocol')
  parser.add_argument('-t', '--tty', help='Spike Hub device path', default='/dev/ttyACM0')
  parser.add_argument('--debug', help='Enable debug', action='store_true')
  parser.set_defaults(func=lambda: parser.print_help())
  sub_parsers = parser.add_subparsers()

  list_parser = sub_parsers.add_parser('list', aliases=['ls'], help='List stored programs')
  list_parser.set_defaults(func=handle_list)

  fwinfo_parser = sub_parsers.add_parser('fwinfo', help='Show firmware version')
  fwinfo_parser.set_defaults(func=handle_fwinfo)

  mvprogram_parser = sub_parsers.add_parser('mv', help='Changes program slot')
  mvprogram_parser.add_argument('from_slot', type=int)
  mvprogram_parser.add_argument('to_slot', type=int)
  mvprogram_parser.set_defaults(func=lambda: rpc.move_project(args.from_slot, args.to_slot))

  cpprogram_parser = sub_parsers.add_parser('upload', aliases=['cp'], help='Uploads a program and stats it. Default slot is 0')
  cpprogram_parser.add_argument('file')
  cpprogram_parser.add_argument('name', nargs='?')
  cpprogram_parser.add_argument('--to_slot', type=int, default=0)
  cpprogram_parser.add_argument('--no_start', '-n', help='Do not start after upload', action='store_true')
  cpprogram_parser.set_defaults(func=handle_upload)

  rmprogram_parser = sub_parsers.add_parser('rm', help='Removes the program at a given slot')
  rmprogram_parser.add_argument('from_slot', type=int)
  rmprogram_parser.set_defaults(func=lambda: rpc.remove_project(args.from_slot))

  startprogram_parser = sub_parsers.add_parser('start', help='Starts a program')
  startprogram_parser.add_argument('slot', type=int)
  startprogram_parser.set_defaults(func=lambda: rpc.program_execute(args.slot))

  stopprogram_parser = sub_parsers.add_parser('stop', help='Stop program execution')
  stopprogram_parser.set_defaults(func=lambda: rpc.program_terminate())

  display_parser = sub_parsers.add_parser('display', help='Controls 5x5 LED matrix display')
  display_parser.set_defaults(func=lambda: display_parser.print_help())
  display_parsers = display_parser.add_subparsers()

  display_image_parser = display_parsers.add_parser('image', help='Displays image on the LED matrix')
  display_image_parser.add_argument('image', help='format xxxxx:xxxxx:xxxxx:xxxxx:xxxx, where x is the pixel brigthness in range 0-9')
  display_image_parser.set_defaults(func=lambda: rpc.display_image(args.image))

  display_text_parser = display_parsers.add_parser('text', help='Displays scrolling text on the LED matrix')
  display_text_parser.add_argument('text')
  display_text_parser.set_defaults(func=lambda: rpc.display_text(args.text))

  display_clear_parser = display_parsers.add_parser('clear', help='Clears display')
  display_clear_parser.set_defaults(func=lambda: rpc.display_clear())

  display_pixel_parser = display_parsers.add_parser('setpixel', help='Sets individual LED brightness')
  display_pixel_parser.add_argument('x', type=int)
  display_pixel_parser.add_argument('y', type=int)
  display_pixel_parser.add_argument('brightness', nargs='?', type=int, default=9, help='pixel brightness 0-9')
  display_pixel_parser.set_defaults(func=lambda: rpc.display_set_pixel(args.x, args.y, args.brightness))

  args = parser.parse_args()
  if args.debug:
    logging.basicConfig(level=logging.DEBUG)
  rpc = RPC(args.tty)
  args.func()
