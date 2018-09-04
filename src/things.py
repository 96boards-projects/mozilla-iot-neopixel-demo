from webthing import (Action, Event, Property, SingleThing, Thing, Value,
                      WebThingServer)
import logging
import time
import uuid
import threading
import smbus

global bus
bus = smbus.SMBus(0)

global neo_on
neo_on = [255,255,255]

global neo_off
neo_off = [0,0,0]

global flag
flag = 0


class OverheatedEvent(Event):

    def __init__(self, thing, data):
        Event.__init__(self, thing, 'overheated', data=data)


class FadeAction(Action):

    def __init__(self, thing, input_):
        Action.__init__(self, uuid.uuid4().hex, thing, 'fade', input_=input_)

    def perform_action(self):
        time.sleep(self.input['duration'] / 1000)
        self.thing.set_property('brightness', self.input['brightness'])
        self.thing.add_event(OverheatedEvent(self.thing, 102))


def make_thing():
    thing = Thing('My Lamp', ['OnOffSwitch', 'Light', 'ColorControl'], 'A web connected lamp')

    def noop(_):
        pass

    thing.add_property(
        Property(thing,
                 'on',
                 Value(True, noop),
                 metadata={
                     '@type': 'OnOffProperty',
                     'label': 'On/Off',
                     'type': 'boolean',
                     'description': 'Whether the lamp is turned on',
                 }))
    thing.add_property(
        Property(thing,
                 'brightness',
                 Value(50, noop),
                 metadata={
                     '@type': 'BrightnessProperty',
                     'label': 'Brightness',
                     'type': 'number',
                     'description': 'The level of light from 0-100',
                     'minimum': 0,
                     'maximum': 100,
                     'unit': 'percent',
                 }))

    thing.add_property(
        Property(thing,
                 'color',
                 Value('#000000', noop),
                 metadata={
                     '@type': 'ColorProperty',
                     'label': 'Color',
                     'type': 'string',
                     'description': 'The Color of light',
                 }))


    thing.add_available_action(
        'fade',
        {
            'label': 'Fade',
            'description': 'Fade the lamp to a given level',
            'input': {
                'type': 'object',
                'required': [
                    'brightness',
                    'duration',
                ],
                'properties': {
                    'brightness': {
                        'type': 'number',
                        'minimum': 0,
                        'maximum': 100,
                        'unit': 'percent',
                    },
                    'duration': {
                        'type': 'number',
                        'minimum': 1,
                        'unit': 'milliseconds',
                    },
                },
            },
        },
        FadeAction)

    thing.add_available_event(
        'overheated',
        {
            'description':
            'The lamp has exceeded its safe operating temperature',
            'type': 'number',
            'unit': 'celsius',
        })

    return thing

def run_neo(a):
    while flag != 1:
           v = bool(a.get_property('on'))
           rbg = int('0x' + a.get_property('color')[1:], 16)
           if v == True:
              for i in range(0, 12):
                   rgb = a.get_property('color')[1:]
                   #print(rbg)
                   b = float(a.get_property('brightness')/100)
                   color = [int((int('0x' + rgb[:2], 16))*b), int((int('0x' + rgb[2:4], 16))*b), int((int('0x' + rgb[4:], 16))*b)]
                   bus.write_i2c_block_data(0x04, i, color)
           else:
              for i in range(0, 12):
                   bus.write_i2c_block_data(0x04, i, neo_off)
           time.sleep(0.2)


def run_server():
    thing = make_thing()
    flag = 0
    server = WebThingServer(SingleThing(thing), port=8888)
    try:
        th = threading.Thread(target=run_neo, args=(thing, ))
        th.deamon = True
        th.start()
        logging.info('starting the server')
        server.start()
    except KeyboardInterrupt:
        logging.info('stopping the server')
        server.stop()
        logging.info('done')


if __name__ == '__main__':
    logging.basicConfig(
        level=10,
        format="%(asctime)s %(filename)s:%(lineno)s %(levelname)s %(message)s"
    )
    run_server()
    flag = 1

