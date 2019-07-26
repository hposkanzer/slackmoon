#!/usr/bin/python

import sys
import subprocess
import httplib
import urllib
import datetime
import calendar
import json

# Updates your Slack status with the emoji for the current phase of the moon.
# Run once a day or so.

# Requires:
#  -Your Slack token in ./.token.
#  -https://github.com/vijinho/moon installed somewhere.
#  -Update moonCommand to point to ^^^.

moonCommand = "/usr/bin/php /Users/hmp/workspace/moon/moon.php"

NEW_MOON = ":new_moon:"
WAXING_CRESCENT = ":waxing_crescent_moon:"
FIRST_QUARTER = ":first_quarter_moon:"
WAXING_GIBBOUS = ":waxing_gibbous_moon:"
FULL_MOON = ":full_moon:"
WANING_GIBBOUS = ":waning_gibbous_moon:"
LAST_QUARTER = ":last_quarter_moon:"
WANING_CRESCENT = ":waning_crescent_moon:"

# Get the phase from a local PHP program.
class PHP():

    def getPhases(self):  # [(seconds, emoji)]
        p = subprocess.Popen(moonCommand, shell=True, stdout=subprocess.PIPE)
        data = json.load(p.stdout)
        #print data
        phases = []  # [(seconds, emoji)]
        self.addPhase(phases, data, "new_moon", NEW_MOON)
        self.addPhase(phases, data, "new_moon_last", NEW_MOON)
        self.addPhase(phases, data, "new_moon_next", NEW_MOON)
        self.addPhase(phases, data, "full_moon", FULL_MOON)
        self.addPhase(phases, data, "full_moon_last", FULL_MOON)
        self.addPhase(phases, data, "full_moon_next", FULL_MOON)
        self.addPhase(phases, data, "first_quarter", FIRST_QUARTER)
        self.addPhase(phases, data, "first_quarter_last", FIRST_QUARTER)
        self.addPhase(phases, data, "first_quarter_next", FIRST_QUARTER)
        self.addPhase(phases, data, "last_quarter", LAST_QUARTER)
        self.addPhase(phases, data, "last_quarter_last", LAST_QUARTER)
        self.addPhase(phases, data, "last_quarter_next", LAST_QUARTER)
        return sorted(phases, key=lambda x: x[0])

    def addPhase(self, phases, data, key, value):
        if (data.has_key(key)):
            phases.append((data[key], value))


# I'd like to get the phase from the USNO's API, but it's not very reliable.
class USNO():

    phaseEmoji = {
        "New Moon": NEW_MOON,
        "First Quarter": FIRST_QUARTER,
        "Full Moon": FULL_MOON,
        "Last Quarter": LAST_QUARTER
    }

    def getPhases(self):  # [(seconds, emoji)]
        now = datetime.datetime.utcnow()
        start_date = (now - datetime.timedelta(15)).strftime("%m/%d/%Y")
        params = urllib.urlencode({
            "date": start_date,
            "nump": 4
        })
        print "GET https://api.usno.navy.mil/moon/phase?date=%s..." % (start_date)
        conn = httplib.HTTPSConnection("api.usno.navy.mil")
        conn.request("GET", "/moon/phase?%s" % (params))
        resp = conn.getresponse()
        print resp.status, resp.reason
        data = resp.read()
        #print data
        conn.close()
        if (resp.status != 200):
            raise RuntimeError("Unable to get phase!")
        phasedata = json.loads(data)["phasedata"]
        phases = []  # [(seconds, emoji)]
        for phase in phasedata:
            s = phase["date"] + " " + phase["time"] + " UTC"
            t = datetime.datetime.strptime(s, "%Y %b %d %H:%M %Z")
            seconds = calendar.timegm(t.timetuple())
            phases.append((seconds, self.phaseEmoji[phase["phase"]]))
        return phases


class SlackMoon():

    def run(self):
        phases = PHP().getPhases()
        emoji = self.getEmoji(phases)
        self.setStatus(emoji)


    interpolatedEmoji = {
        (NEW_MOON, FIRST_QUARTER): WAXING_CRESCENT,
        (FIRST_QUARTER, FULL_MOON): WAXING_GIBBOUS,
        (FULL_MOON, LAST_QUARTER): WANING_GIBBOUS,
        (LAST_QUARTER, NEW_MOON): WANING_CRESCENT
    }

    # now = The current time, in seconds.
    # phases = [(seconds, emoji)]
    def getEmoji(self, phases):
        interpolatedPhases = []  # [(seconds, emoji)]
        for i in range(len(phases)-1):
            thisPhase = phases[i]
            nextPhase = phases[i+1]
            interpolatedPhases.append(thisPhase)
            interpolatedSeconds = (thisPhase[0] + nextPhase[0])/2.0
            interpolatedEmoji = self.interpolatedEmoji[(thisPhase[1], nextPhase[1])]
            interpolatedPhases.append((interpolatedSeconds, interpolatedEmoji))
        lastPhase = phases[len(phases)-1]
        interpolatedPhases.append(lastPhase)
        #print interpolatedPhases
        minDiff = sys.maxint
        emoji = ""
        nowSeconds = calendar.timegm(datetime.datetime.utcnow().timetuple())
        for (phaseT, phaseE) in interpolatedPhases:
            diff = abs(nowSeconds - phaseT)
            if (diff < minDiff):
                minDiff = diff
                emoji = phaseE
        return emoji


    def setStatus(self, emoji):
        token = self.loadToken()
        headers = {
            "Content-type": "application/x-www-form-urlencoded"
        }
        params = urllib.urlencode({
            "token": token,
            "profile": {
                "status_text": "",
                "status_emoji": emoji
            },
            "pretty": 1
        })
        print "POST https://slack.com/api/users.profile.set?status_emoji=%s..." % (emoji)
        conn = httplib.HTTPSConnection("slack.com")
        conn.request("POST", "/api/users.profile.set", params, headers)
        resp = conn.getresponse()
        print resp.status, resp.reason
        data = resp.read()
        #print data
        conn.close()
        if (resp.status != 200):
            raise RuntimeError("Unable to set status!")

    def loadToken(self):
        f = open(".token")
        token = f.read()
        f.close()
        return token

if __name__ == '__main__':
    SlackMoon().run()
