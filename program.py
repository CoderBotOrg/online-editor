############################################################################
#    CoderBot, a didactical programmable robot.
#    Copyright (C) 2014, 2015 Roberto Previtera <info@coderbot.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
############################################################################

import os
import threading
import json
import logging

import math
from tinydb import TinyDB, Query
from tinydb_appengine.storages import EphemeralJSONStorage

import coderbot
import config


PROGRAM_PATH = "./data/"
PROGRAM_PREFIX = "program_"
PROGRAM_SUFFIX = ".json"

def get_cam():
    return camera.Camera.get_instance()

def get_bot():
    return coderbot.CoderBot.get_instance()

def get_motion():
    return motion.Motion.get_instance()

def get_audio():
    return audio.Audio.get_instance()

def get_prog_eng():
    return ProgramEngine.get_instance()

def get_event():
    return event.EventManager.get_instance()

class ProgramEngine:

    # pylint: disable=exec-used

    _instance = None

    def __init__(self):
        self._program = None
        self._log = ""
        self._programs = TinyDB("data/programs.json", storage=EphemeralJSONStorage)
        query = Query()
        for dirname, dirnames, filenames, in os.walk(PROGRAM_PATH):
            dirnames
            for filename in filenames:
                if PROGRAM_PREFIX in filename:
                    program_name = filename[len(PROGRAM_PREFIX):-len(PROGRAM_SUFFIX)]
                    if self._programs.search(query.name == program_name) == []:
                        logging.info("adding program %s in path %s as default %r", program_name, dirname, ("default" in dirname))
                        self._programs.insert({"name": program_name, "filename": os.path.join(dirname, filename), "default": str("default" in dirname)})

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = ProgramEngine()
        return cls._instance

    def prog_list(self):
        return self._programs.all()

    def save(self, program):
        query = Query()
        self._program = program
        program_db_entry = program.as_dict()
        program_db_entry["filename"] = os.path.join(PROGRAM_PATH, PROGRAM_PREFIX + program.name + PROGRAM_SUFFIX)
        if self._programs.search(query.name == program.name) != []:
            self._programs.update(program_db_entry, query.name == program.name)
        else:
            self._programs.insert(program_db_entry)
        f = open(program_db_entry["filename"], 'r')
        json.dump(program.as_dict(), f)
        f.close()

    def load(self, name):
        query = Query()
        program_db_entries = self._programs.search(query.name == name)
        if program_db_entries != []:
            logging.info(program_db_entries[0])
            f = open(program_db_entries[0]["filename"], 'r')
            self._program = Program.from_dict(json.load(f))
        return self._program

    def delete(self, name):
        query = Query()
        program_db_entries = self._programs.search(query.name == name)
        if program_db_entries != []:
            os.remove(program_db_entries[0]["filename"])
            self._programs.remove(query.name == name)

    def create(self, name, code):
        self._program = Program(name, code)
        return self._program

    def is_running(self, name):
        return self._program.is_running() and self._program.name == name

    def check_end(self):
        return self._program.check_end()

    def log(self, text):
        self._log += text + "\n"

    def get_log(self):
        return self._log

class Program:
    _running = False

    @property
    def dom_code(self):
        return self._dom_code

    def __init__(self, name, code=None, dom_code=None, default=False):
        #super(Program, self).__init__()
        self._thread = None
        self.name = name
        self._dom_code = dom_code
        self._code = code
        self._default = default

    def execute(self):
        if self._running:
            raise RuntimeError('already running')

        self._running = True

        try:
            self._thread = threading.Thread(target=self.run)
            self._thread.start()
        except RuntimeError as re:
            logging.error("RuntimeError: %s", str(re))
        except Exception as e:
            logging.error("Exception: %s", str(e))

        return "ok"

    def end(self):
        if self._running:
            self._running = False
            self._thread.join()

    def check_end(self):
        if self._running is False:
            raise RuntimeError('end requested')
        return None

    def is_running(self):
        return self._running

    def is_default(self):
        return self._default

    def run(self):
        try:
            program = self
            try:
                if config.Config.get().get("prog_video_rec") == "true":
                    get_cam().video_rec(program.name)
                    logging.debug("starting video")
            except Exception:
                logging.error("Camera not available")

            imports = "import json\n"
            code = imports + self._code
            env = globals()
            exec(code, env, env)
        except RuntimeError as re:
            logging.info("quit: %s", str(re))
            get_prog_eng().log(str(re))
        except Exception as e:
            logging.info("quit: %s", str(e))
            get_prog_eng().log(str(e))
        finally:
            try:
                get_event().wait_event_generators()
                get_event().unregister_listeners()
                get_event().unregister_publishers()
            except Exception:
                logging.error("error polishing event system")
            try:
                get_cam().video_stop() #if video is running, stop it
                get_cam().set_text("") #clear overlay text (if any)
                get_motion().stop()
            except Exception:
                logging.error("Camera not available")
            self._running = False


    def as_dict(self):
        return {'name': self.name,
                'dom_code': self._dom_code,
                'code': self._code,
                'default': self._default}

    @classmethod
    def from_dict(cls, amap):
        return Program(name=amap['name'], dom_code=amap['dom_code'], code=amap['code'], default=amap.get('default', False))
