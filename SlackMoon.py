#!/usr/bin/python

import sys
import httplib
import urllib
import datetime
import calendar
import json

class SlackMoon():

    def run(self):
        phase = self.getPhase()
        self.setStatus(phase)

    def getPhase(self):
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
        return self.getEmoji(now, json.loads(data))

    phaseEmoji = {
        "New Moon": ":new_moon:",
        "First Quarter": ":first_quarter_moon:",
        "Full Moon": ":full_moon:",
        "Last Quarter": ":last_quarter_moon:"
    }
    interpolatedEmoji = {
        ("New Moon", "First Quarter"): ":waxing_crescent_moon:",
        ("First Quarter", "Full Moon"): ":waxing_gibbous_moon:",
        ("Full Moon", "Last Quarter"): ":waning_gibbous_moon:",
        ("Last Quarter", "New Moon"): ":waning_crescent_moon:"
    }

    def getEmoji(self, now, data):
        phases = [] # [(seconds, phase name)]
        for phase in data["phasedata"]:
            s = phase["date"] + " " + phase["time"] + " UTC"
            t = datetime.datetime.strptime(s, "%Y %b %d %H:%M %Z")
            seconds = calendar.timegm(t.timetuple())
            phases.append((seconds, phase["phase"]))
        interpolatedPhases = [] # [(seconds, emoji)]
        for i in range(len(phases)-1):
            thisPhase = phases[i]
            nextPhase = phases[i+1]
            interpolatedPhases.append((thisPhase[0], self.phaseEmoji[thisPhase[1]]))
            interpolatedSeconds = (thisPhase[0] + nextPhase[0])/2.0
            interpolatedEmoji = self.interpolatedEmoji[(thisPhase[1], nextPhase[1])]
            interpolatedPhases.append((interpolatedSeconds, interpolatedEmoji))
        lastPhase = phases[len(phases)-1]
        interpolatedPhases.append(lastPhase)
        minDiff = sys.maxint
        emoji = ""
        nowSeconds = calendar.timegm(now.timetuple())
        for (phaseT, phaseE) in interpolatedPhases:
            diff = abs(nowSeconds - phaseT)
            if (diff < minDiff):
                minDiff = diff
                emoji = phaseE
        return emoji

    def setStatus(self, phase):
        token = self.loadToken()
        headers = {
            "Content-type": "application/x-www-form-urlencoded"
        }
        params = urllib.urlencode({
            "token": token,
            "profile": {
                "status_text": "",
                "status_emoji": phase
            },
            "pretty": 1
        })
        print "POST https://slack.com/api/users.profile.set?status_emoji=%s..." % (phase)
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