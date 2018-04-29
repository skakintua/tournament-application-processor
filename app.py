from pyquery import PyQuery as pq
from urllib.request import urlopen
from operator import itemgetter
import sys, urllib, json

"""
    @name: Application Processor for NTUA Chess Tournaments
    @author: Theodore Diamantidis
    @email: diamaltho@gmail.com
    @organization: Le Roi NTUA Chess Team
    @git: https://github.com/skakintua
    @description:
    This program reads a CSV file stored in (argv[1]) that contains the list of the submitted applications.
    The candidate players are firstly sorted by FIDE ELO and the first (LIMIT_FIDE) are chosen.
    The rest of the players are then sorted primarily by whether they are NTUA students and secondarily by their application datetime (earlier applications take precedence).
    In the second selection, the program chooses as many players from the rest as necessary to fill (LIMIT) positions in total.
    The selected players are exported in (argv[2])/results.txt in table form.
    Their emails are exported in (argv[2])/emails.txt separated by a comma for quick addition to e-mail recipients.
    Finally, a CSV file suitable for insertion in the Blitz Arena platform is exported in (argv[2])/final.csv.
"""

FIDE_URL = "http://ratings.fide.com/card.phtml?event="
# Total limit of players
LIMIT = 64
# Limit of players that will be accepted for being in FIDE
LIMIT_FIDE = 32

players = []
confirmed = []

if len(sys.argv) < 3:
    print("Usage: app.py (csv file) (storage directory)")
    sys.exit()

try:
    with open(sys.argv[1]) as f:
        lines = f.readlines()
        lines = lines[1:]
        for index, line in enumerate(lines):
            if index == len(lines) - 1:
                l = line.split(",")
            else:
                # Remove new line for all but the last line
                l = line[:-1].split(",")
            players.append([ \
                1000, \
                l[5] != 'Άλλο' and l[5] != '', \
                l[0], l[1], l[2], l[3], l[4], l[5], l[6] \
            ])
except FileNotFoundError:
    print("File not found")
    sys.exit()

if len(sys.argv) > 2:
    try:
        with open(sys.argv[2] + '/confirmed.txt') as f:
            lines = f.readlines()
            for index, line in enumerate(lines):
                if index == len(lines) - 1:
                    confirmed.append(line)
                else:
                    # Remove new line for all but the last line
                    confirmed.append(line[:-1])
    except FileNotFoundError:
        pass

# Association between fields and p indices
ELO, IS_NTUA, DATETIME, NAME, EMAIL, PHONE, FIDE_ID, SCHOOL, STYEAR = tuple(range(9))

player_sort = []

for p in players:
    if p[FIDE_ID] != '' and p[FIDE_ID] != '-':
        ''' Fetch FIDE name '''
        f = urlopen(FIDE_URL + p[FIDE_ID]).read().decode('utf-8')
        if p[FIDE_ID] not in confirmed:
            fideid_i = f.find('<td bgcolor=#efefef width=230 height=20>&nbsp;')
            fideid_j = -1
            if fideid_i >= 0:
                fideid_i += len('<td bgcolor=#efefef width=230 height=20>&nbsp;')
                fideid_j = f.find('</td>', fideid_i)
            if fideid_i >= 0 and fideid_j >= 0:
                answer = input("Does '{}' match with '{}'? Y/n".format(f[fideid_i : fideid_j], p[NAME]))
                if not(answer == '' or answer == 'Y' or answer == 'y'):
                    p[FIDE_ID] = ''
                else:
                    confirmed.append(p[FIDE_ID])
            else:
                p[FIDE_ID] = ''
        if p[FIDE_ID] in confirmed:
            ''' Fetch FIDE ratings '''
            std, rapid, blitz = (0, 0, 0)
            # STD
            std_i = f.find('<small>std.</small><br>')
            std_j = -1
            if std_i >= 0:
                std_i += len('<small>std.</small><br>')
                std_j = f.find('</td>', std_i)
            if std_i >= 0 and std_j >= 0:
                std = f[std_i : std_j].strip()
                if std == 'Not rated':
                    std = 0
                else:
                    std = int(std)
            # RAPID
            rapid_i = f.find('<small>rapid</small><br><font color=red>')
            rapid_j = -1
            if rapid_i >= 0:
                rapid_i += len('<small>rapid</small><br><font color=red>')
                rapid_j = f.find('</font>', rapid_i)
            if rapid_i >= 0 and rapid_j >= 0:
                rapid = int(f[rapid_i : rapid_j])
            # BLITZ
            blitz_i = f.find('<small>blitz</small><br><font color=blue>')
            blitz_j = -1
            if blitz_i >= 0:
                blitz_i += len('<small>blitz</small><br><font color=blue>')
                blitz_j = f.find('</font>', blitz_i)
            if blitz_i >= 0 and blitz_j >= 0:
                blitz = int(f[blitz_i : blitz_j])
            # Choose ELO by precedence of blitz, rapid then std. If none, then set ELO to 1000
            if std > 0:
                p[ELO] = std
            if rapid > 0:
                p[ELO] = rapid
            if blitz > 0:
                p[ELO] = blitz
            p[ELO] = max(p[ELO], 1000)
    if p[FIDE_ID] == '-':
        p[FIDE_ID] = ''
    player_sort.append(tuple(p))

# Get first (LIMIT_FIDE) FIDE players. If ELO points are same, earlier applications take precedence
player_sort.sort(key=itemgetter(DATETIME))
player_sort.sort(key=itemgetter(ELO), reverse=True)
first_fide = list(filter(lambda p: p[FIDE_ID] != '', player_sort))
first_fide = first_fide[:LIMIT_FIDE]
# Get rest of players
rest = player_sort[len(first_fide) - 1 :]

# Rest players are sorted by IS_NTUA as primary key and date of application as secondary key
# Sort ascending by date; Older entries take precedence
rest.sort(key=itemgetter(DATETIME))
# Sort descending by IS_NTUA; NTUA students take precedence
rest.sort(key=itemgetter(IS_NTUA), reverse=True)

# Remove last players to satisfy LIMIT
if len(first_fide) + len(rest) > LIMIT:
    rest = rest[: (LIMIT - len(first_fide))]

# Final player list
final = first_fide + rest
with open(sys.argv[2] + '/results.txt', 'w') as f:
    for p in final:
        f.write("{:32s} ({}) {:^16} {}\n".format(p[NAME], p[ELO], "NTUA" if p[IS_NTUA] else "Not NTUA", p[DATETIME]))
with open(sys.argv[2] + '/emails.txt', 'w') as f:
    emails = [p[EMAIL] for p in final]
    f.write(",".join(emails))
with open(sys.argv[2] + '/final.csv', 'w') as f:
    for p in final:
        first, last = p[NAME].split()
        f.write('{},{},{},{}\n'.format(first, last, p[FIDE_ID], p[ELO]))

if len(sys.argv) > 2:
    with open(sys.argv[2] + '/confirmed.txt', 'w') as f:
        f.write("\n".join(confirmed))

