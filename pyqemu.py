#!/usr/bin/env python

import os
import sys
import zlib
import yaml
import logging
import subprocess

from pycli_tools.commands import Command, arg

log = logging.getLogger(__name__)

def generate_mac(name):
    crc = zlib.crc32(name.encode("utf-8")) & 0xffffffff
    crc = str(hex(crc))[2:]

    return "52:54:%s%s:%s%s:%s%s:%s%s" % tuple(crc)

class Box(object):
    @classmethod
    def factory(cls_object, qemufile="Qemufile"):
        if not os.path.exists(qemufile):
            return []

        with open(qemufile, 'r') as file:
            content = yaml.load(file)

        boxes = []
        for name in content:
            box = Box(name, content[name])
            boxes.append(box)
        return boxes

    def __init__(self, name, definition):
        self.name = name
        self.definition = definition

        self.validate_image()

    def validate_image(self):
        try:
            image_def = self.definition['image']
        except KeyError:
            self.image = None
            return

        if isinstance(image_def, str):
            self.image = {
                'file': image_def,
                'type': 'qcow2',
                'size': '512M',
            }
        elif not image_def:
            self.image = {
                'file': '{0}.img'.format(self.name),
                'type': 'qcow2',
                'size': '512M',
            }
        else:
            self.image = image_def

    def __repr__(self):
        return '<Box {0}>'.format(self.name)

    def create_image(self):
        if not self.image:
            return

        if os.path.exists(self.image['file']):
            log.info("Image file already exists")
            return

        command = [
            'qemu-img', 'create',
            '-f', self.image['type'],
            self.image['file'],
            self.image['size']
        ]
        log.info(' '.join(command))
        return subprocess.call(command)

    def start(self):
        self.create_image()

        arch = self.definition.get('architecture', 'x86_64')

        command  = [
            'qemu-system-{0}'.format(arch)
        ]

        if 'args' in self.definition:
            command += self.definition.get('args').split(' ')

        if self.image:
            command += [self.image['file']]

        log.info(' '.join(command))

        return subprocess.call(command)




class ListBoxesCommand(Command):
    '''list qemu boxes'''
    name = 'list'

    def run(self, args, parser, boxes):
        for box in boxes:
            print(box.name)

class StartBoxCommand(Command):
    '''start a qemu box'''
    name = 'start'
    args = [
        arg('box', nargs="?", default="default",
            help='the name of the box to start'),
    ]

    def run(self, args, parser, boxes):
        the_box = None
        for box in boxes:
            if args.box == box.name:
                the_box = box
                break

        if the_box:
            the_box.start()
        else:
            self.app.log.error('No box found with name ' + args.box)
            return 1

class GenerateMacCommand(Command):
    '''generate a mac address'''
    name = 'generate-mac'
    args = [
        arg('string', help='a string to use as the basis for the mac address'),
    ]

    def run(self, args, parser, boxes):
        print(generate_mac(args.string))


def main():
    from pycli_tools.parsers import get_argparser

    parser = get_argparser(
        prog='pyqemu',
        version='0.1.0',
        logging_format='[%(asctime)-15s] %(levelname)s %(message)s',
    )

    parser.add_argument('--qemufile', default="Qemufile",
        help='the name of the Qemufile to read boxes from',
    )

    parser.add_commands([
        ListBoxesCommand(),
        StartBoxCommand(),
        GenerateMacCommand(),
    ])

    args = parser.parse_args()

    if 'func' not in args:
        parser.print_help()
    else:
        args.func(args, parser=parser, boxes=Box.factory(args.qemufile))

if '__main__' == __name__:
    main()
