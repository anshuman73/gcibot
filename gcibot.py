#!/usr/bin/env python
# -*- coding: utf-8 -*-
# GCI bot.
# Parse tasks data and show info about them
# Copyright (C) Ignacio Rodríguez <ignacio@sugarlabs.org>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging
import data
import json
import requests
import re
import sys

from twisted.internet import reactor, protocol
from twisted.words.protocols import irc


logging.basicConfig(level=logging.DEBUG)

ABOUT = "I'm a bot written by Ignacio, paste GCI link task and \
I will tell data about it.\nSource code available in: https://github.com/i5o/gcibot"

ORGS = {5149586599444480: "Apertium",
        4923366913867776: "Copyleft Games",
        4603782423904256: "Drupal",
        4625502878826496: "FOSSASIA",
        6583394590785536: "Haiku",
        6015066264567808: "KDE",
        5413855668731904: "MetaBrainz Foundation",
        5966051024044032: "OpenMRS",
        5167877522980864: "RTEMS Project",
        5340425418178560: "Sugar Labs",
        4866017020870656: "SCoRe",
        5748107203575808: "Systers",
        4568116747042816: "Ubuntu",
        5505623550590976: "Wikimedia"}


API_LINK = "https://codein.withgoogle.com/api/program/2015/taskdefinition/{taskid}/"
REGEX_TASKS_1 = re.compile(
    ur'https{0,1}:\/\/codein\.withgoogle\.com\/tasks\/([0-9]+)\/{0,1}')
REGEX_TASKS_2 = re.compile(
    ur'https{0,1}:\/\/codein\.withgoogle\.com\/dashboard\/task-instances\/([0-9]+)\/{0,1}')
REDIRECT = 'https://codein.withgoogle.com/dashboard/task-instances/{taskid}/'


class GCIBot(irc.IRCClient):
    nickname = data.nickname
    username = data.username
    password = data.password

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)

    def signedOn(self):
        for c in self.factory.channels:
            self.join(c)

    def privmsg(self, user, channel, msg):
        tasks = []

        try:
            tasks = self.find_tasks(msg)
        except Exception as error:
            logging.warning("** Error (%s) **" % error)
            logging.warning(msg)

        for task in tasks:
            self.msg(channel, task)

        messaging_me = msg.startswith(
            self.nickname +
            ":") or msg.startswith(
            self.nickname +
            ",") or msg.startswith(
            self.nickname +
            " ")

        user = user.split('!', 1)[0]
        if messaging_me:
            if "ping" in msg.lower():
                self.msg(channel, "%s, pong" % user)

            if "about" in msg.lower():
                self.msg(channel, "%s, %s" % (user, ABOUT))

            if "rules" in msg.lower():
                self.msg(channel, "%s, https://developers.google.com/open-source/gci/resources/contest-rules" % user)

            if "guide" in msg.lower():
                self.msg(channel, "%s, https://developers.google.com/open-source/gci/resources/getting-started" % user)

            if "faq" in msg.lower():
                self.msg(channel, "%s, https://developers.google.com/open-source/gci/faq" % user)

            if "timeline" in msg.lower():
                self.msg(channel, "%s, https://developers.google.com/open-source/gci/timeline" % user)

    def find_tasks(self, msg):
        msg_tasks = []
        tasks_id = []
        tasks_id_1 = re.findall(REGEX_TASKS_1, msg)
        tasks_id_2 = re.findall(REGEX_TASKS_2, msg)

        for id1 in tasks_id_1:
            if id1 not in tasks_id:
                tasks_id.append([0, id1])

        for id2 in tasks_id_2:
            if id2 not in tasks_id:
                tasks_id.append([1, id2])

        done = []
        for task in tasks_id:

            if task[0]:
                f = requests.get(REDIRECT.format(taskid=task[1]))
                task = [0, re.findall(REGEX_TASKS_1, f.url)[0]]

            json_ = requests.get(API_LINK.format(taskid=task[1]))
            json_task = json.loads(json_.text)

            msg = "{title} || {days} || {categories} || {org} {whatever}"
            int_days = json_task["time_to_complete_in_days"]

            cat_txt = {1: "Code",
                       2: "User Interface",
                       3: "Documentation",
                       4: "QA",
                       5: "Outreach / Research"}

            categories = ""
            for cat in json_task["categories"]:
                categories += ", " + cat_txt[cat]

            categories = categories[2:]

            whatever = ""

            claimed = int(json_task["in_progress_count"]) >= 1
            all_instances_done = int(
                json_task["completed_count"]) == int(
                json_task["max_instances"])
            multiple_instances = int(json_task["max_instances"]) > 1

            if claimed:
                whatever += "|| Currently claimed "

            if all_instances_done:
                whatever += "|| All instances done "

            if multiple_instances:
                whatever += "|| Instances: %d/%d " % (
                    int(json_task["claimed_count"]), int(json_task["max_instances"]))

            if json_task["is_beginner"]:
                whatever += "|| Beginner task "

            if task[1] in done:
                return
            else:
                done.append(task[1])

            d = msg.format(
                title=json_task['name'],
                days="%d days" %
                int_days,
                categories=categories,
                org=ORGS[json_task["organization_id"]],
                whatever=whatever)

            msg_tasks.append(d)

        return msg_tasks


class BotFactory(protocol.ClientFactory):

    def __init__(self, channels):
        self.channels = channels

    def buildProtocol(self, addr):
        p = GCIBot()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        logging.error("** Conection failed ** ")
        reactor.stop()


if __name__ == '__main__':
    logging.info('** Starting GCIBot **')
    f = BotFactory(sys.argv[1:])
    reactor.connectTCP("irc.freenode.net", 6667, f)
    logging.info('** Connected to server **')
    logging.info('** Channels: %s **' % ", ".join(sys.argv[1:]))
    reactor.run()
