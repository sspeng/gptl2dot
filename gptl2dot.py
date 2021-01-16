#!/usr/bin/python2

# Author: Xiaohui Duan <sunrise.duan@mail.sdu.edu.cn>

import re
import sys
import argparse
parser = argparse.ArgumentParser(description="Convert GPTL detailed timing to dot file.")
parser.add_argument("-r", "--root", action="store", default = None, help="Root timer node")
parser.add_argument("-t", "--thres", action="store", type=float, default = 0, help="Threshold for create node in graph [0..1]")
parser.add_argument("-o", "--outfile", action="store", default=None, help="Input file")
parser.add_argument("-i", "--infile", action="store", default=None, help="Output file")
parser.add_argument("-c", "--color", action="store", default="pink", choices=["pink", "forest", "desert", "ocean", "fire"], help="Color scheme")

arg = parser.parse_args(sys.argv[1:])
color_schemes = {
    "pink": (255, 192, 203),
    "forest": (0, 192, 0),
    "desert": (192, 192, 0),
    "ocean" : (0, 0, 192),
    "fire" : (255, 0, 0)
    }
timing_start_re = re.compile('\\s+Called\\s+Recurse\\s+Wallclock\\s+max\\s+min\\s+self_OH\\s+parent_OH\\s*')
timing_end_re = re.compile("Overhead sum.*")

infile = sys.stdin
outfile = sys.stdout
if arg.infile is not None:
    infile = open(arg.infile)
if arg.outfile is not None:
    outfile = open(arg.outfile, 'w')

#timing_start_re = re.compile('\\s*lc_rof_export')
#timing_end_re = re.compile('\\s*CPL:C2O_INITWAIT')
spacing_re = re.compile('[\\*\\s]*')
def create_timer(line):
    sp = spacing_re.split(line.rstrip())
    if len(sp) < 8:
        return None
    indent = spacing_re.match(line).end()
    n_name_tile = len(sp) - 7
    #print n_name_tile, sp,len(sp)
    name = ' '.join(sp[:n_name_tile])
    suffix = sp[n_name_tile:]
    ncall = float(suffix[0])
    wallclock = float(suffix[2])
    #maxtime = float(sp[3])
    #mintime = float(sp[4])
    return (name, indent, ncall, wallclock)

timers = {}
calls = {}
enabled = False
inroot = False
#timers['Enterance'] = (0, 0)
call_stack = [(0, 'Enterance')]
lastindent = 0
for line in infile:
    if timing_start_re.match(line) is not None:
        enabled = True
    elif timing_end_re.match(line) is not None:
        enabled = False
    elif enabled:
        #print line
        timer = create_timer(line)
        if timer is not None:
            if arg.root is None:
                timers[timer[0]] = timer[2:]
                indent = timer[1]
                while len(call_stack) > 0 and indent <= call_stack[-1][0]:
                    call_stack.pop()
                calls[(call_stack[-1][1], timer[0])] = True
                call_stack.append((indent, timer[0]))
            else:
                if timer[0].strip() == arg.root:
                    inroot = True
                    indent = timer[1]
                    timers[timer[0]] = timer[2:]
                    calls[(call_stack[-1][1], timer[0])] = True
                    call_stack.append((indent, timer[0]))
                elif inroot:
                    indent = timer[1]
                    while len(call_stack) > 0 and indent <= call_stack[-1][0]:
                        call_stack.pop()
                    #print len(call_stack), call_stack, line
                    if len(call_stack) == 1:
                        break
                    timers[timer[0]] = timer[2:]
                    calls[(call_stack[-1][1], timer[0])] = True
                    call_stack.append((indent, timer[0]))
                    
#print timers
#print calls

color_end = color_schemes[arg.color]
color_start = tuple(map(lambda x: int(x * 0.3 + 0.5), color_end))
def get_color(ratio):
    new_color = tuple(map(lambda x, y: x * ratio + y * (1 - ratio), color_start, color_end))
    new_color_int = tuple(map(lambda x: int(x + 0.5), new_color))
    return "#%02x%02x%02x" % new_color_int
# colors = ['#CD0000', '#3CB371', '#000080', '#DBDBDB']
# def get_color(ratio):
#     #print ratio
#     return colors[int(min(ratio / 0.25, 3))]
total_time = 0
for k in calls.keys():
    if k[0] == 'Enterance':
        total_time += timers[k[1]][1]
outfile.write('digraph {\n')
outfile.write('\tgraph [fontname=Arial, nodesep=0.5, ranksep=1];\n')
outfile.write('\tnode [fontcolor=white, fontname=Arial, height=0, shape=box, style=filled, width=0];\n')
outfile.write('\tedge [fontname=Arial];\n')
timers_present = {}
for k, v in timers.items():
    if k != 'Enterance':
        ratio = v[1] / total_time
        color = get_color(ratio)
        if ratio > arg.thres:
            outfile.write('\t"%s" [color="%s", label="%s\\n%.0f\\n%f\\n%f%%"];\n' % (k.lstrip(), color, k.lstrip(), v[0], v[1], ratio * 100))
            timers_present[k.strip()] = True
for k in calls.keys():
    if k[0] != 'Enterance' and k[0].strip() in timers_present and k[1].strip() in timers_present:
        outfile.write('\t"%s" -> "%s" [arrowsize="0.35"];\n' % (k[0].lstrip(), k[1].lstrip()))
outfile.write('}\n')
