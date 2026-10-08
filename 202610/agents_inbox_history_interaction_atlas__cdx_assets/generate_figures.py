#!/usr/bin/env python3
"""Generate precise terminal concept diagrams in SVG and PNG (Pillow only)."""
from pathlib import Path
from html import escape
import json
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
BASE = 'agents_inbox_history_interaction_atlas'
for attempt in range(100):
    stem = f'{BASE}{"" if attempt == 0 else "_" + str(attempt + 1)}__cdx'
    report = ROOT / '202610' / f'{stem}.md'
    assets = report.with_name(stem + '_assets')
    if not report.exists() and not assets.exists():
        assets.mkdir(parents=True, exist_ok=False)
        break
else:
    raise RuntimeError('Could not allocate a new report filename')

SCALE = 2
BG, PANEL, EDGE = '#0B101A', '#111C2B', '#34445C'
FG, MUTED, GOLD, CYAN, GREEN, RED = '#E7EDF7', '#B3BED0', '#EBC575', '#79D5DF', '#9BE0AF', '#FFA3A3'
FONTROOT = Path('/usr/share/fonts/truetype/dejavu')

class Canvas:
    def __init__(self, w, h, title, subtitle):
        self.w, self.h = w, h
        self.image = Image.new('RGB', (w * SCALE, h * SCALE), BG)
        self.d = ImageDraw.Draw(self.image)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img"><title>{escape(title)}</title><desc>{escape(subtitle)}</desc><rect width="100%" height="100%" fill="{BG}"/>']
        self.text(36, 24, title, 30, GOLD, mono=False, bold=True)
        self.text(36, 72, subtitle, 16, MUTED, mono=False)
    def rect(self, x, y, w, h, fill=PANEL, outline=EDGE, width=1):
        self.d.rectangle([x*SCALE,y*SCALE,(x+w)*SCALE,(y+h)*SCALE],fill=fill,outline=outline,width=width*SCALE)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{outline}" stroke-width="{width}"/>')
    def line(self, x1,y1,x2,y2, color=EDGE, width=1):
        self.d.line([x1*SCALE,y1*SCALE,x2*SCALE,y2*SCALE],fill=color,width=width*SCALE)
        self.svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')
    def text(self,x,y,s,size=16,color=FG,mono=True,bold=False):
        family = 'DejaVuSansMono' if mono else 'DejaVuSans'
        font=ImageFont.truetype(str(FONTROOT / (family + ('-Bold' if bold else '') + '.ttf')),size*SCALE)
        self.d.text((x*SCALE,y*SCALE),s,font=font,fill=color,anchor='lt')
        self.svg.append(f'<text x="{x}" y="{y}" dominant-baseline="text-before-edge" font-family="{"DejaVu Sans Mono, monospace" if mono else "DejaVu Sans, sans-serif"}" font-size="{size}" font-weight="{"bold" if bold else "normal"}" fill="{color}">{escape(s)}</text>')
    def lines(self,x,y,ss,size=16,color=FG,gap=27,mono=True):
        for i,s in enumerate(ss): self.text(x,y+i*gap,s,size,color,mono)
    def arrow(self,x1,y1,x2,y2,color=CYAN):
        self.line(x1,y1,x2,y2,color,2)
        if x2>x1: self.line(x2-10,y2-6,x2,y2,color,2); self.line(x2-10,y2+6,x2,y2,color,2)
        elif y2>y1: self.line(x2-6,y2-10,x2,y2,color,2); self.line(x2+6,y2-10,x2,y2,color,2)
    def save(self,name):
        png=assets / f'{name}.png'; svg=assets / f'{name}.svg'
        with png.open('xb') as f: self.image.save(f,format='PNG',optimize=True)
        with svg.open('x') as f: f.write('\n'.join(self.svg + ['</svg>']))

class Terminal:
    CW, RH = 9.7, 24
    def __init__(self,c,x,y,cols,rows):
        self.c,self.x,self.y,self.cols,self.rows=c,x,y,cols,rows
        c.rect(x-10,y-10,cols*self.CW+20,rows*self.RH+20)
    def at(self,col,row,s,color=FG,bold=False):
        assert len(s) + col <= self.cols, (col,row,s,len(s),self.cols)
        assert row < self.rows
        self.c.text(self.x+col*self.CW,self.y+row*self.RH,s,16,color,bold=bold)
    def fill(self,col,row,width,fill):
        self.c.rect(self.x+col*self.CW-3,self.y+row*self.RH-2,width*self.CW,self.RH,fill,fill)
    def divider(self,col,row1,row2):
        self.c.line(self.x+col*self.CW,self.y+row1*self.RH,self.x+col*self.CW,self.y+row2*self.RH,EDGE)

def chrome(t,history=False,published=False):
    t.at(0,0,'SASE   [ Agents ]    Artifacts    Services',GOLD,True)
    t.at(107,0,'sase   |   2 running  1 input',MUTED)
    t.at(0,2,'Inbox  |  [ History ]' if history else '[ Inbox ]  |  History',CYAN,True)
    t.at(30,2,',a switch   |   Project: sase',MUTED)
    if history:
        t.at(0,3,'Source: Published project v' if published else 'Source: This machine v',CYAN)
        t.at(31,3,'Group: Date v    Time: Any time v    Hidden: excluded',MUTED)
    else:
        t.at(0,3,'[ main ]    research    ops    |    ] / [ agent placement tabs',MUTED)

c=Canvas(1560,650,'01 / One agent destination, two jobs','Concept map. Gold = agent destination; text labels carry the distinctions.')
c.rect(36,120,660,390); c.text(60,140,'CURRENT',18,MUTED,bold=True)
c.text(60,185,'Agents',26,GOLD,mono=False,bold=True)
c.lines(60,233,['Watch · answer · inspect decks','Non-dismissed inbox + placement tabs'],18,FG,mono=False)
c.line(60,307,667,307)
c.text(60,330,'Artifacts > Agent',26,GOLD,mono=False,bold=True)
c.lines(60,381,['Find old identity · inspect metadata · revive','Good historical viewer requires restoration'],18,FG,mono=False)
c.arrow(709,310,805,310)
c.rect(822,120,699,390); c.text(846,140,'PROPOSED',18,MUTED,bold=True)
c.text(846,184,'Agents',28,GOLD,mono=False,bold=True)
c.rect(846,235,285,165); c.text(866,253,'[ Inbox ]',22,CYAN,bold=True)
c.lines(866,300,['Operational tree','Placement + tribes','Unread and attention'],16)
c.rect(1155,235,342,165); c.text(1175,253,'[ History ]',22,CYAN,bold=True)
c.lines(1175,300,['Searchable catalog','No placement strip','Read without restoring'],16)
c.text(846,439,'Shared identity · detail decks · links',18,GOLD,mono=False,bold=True)
c.lines(36,553,['The switch changes the browsing task. It never moves an agent to a new placement tab.',
                'Artifacts retains Stitch, Patch, Bead, document providers, and File.'],19,MUTED,mono=False,gap=31)
c.save('01_destination_map')

c=Canvas(1560,940,'02 / Inbox keeps its operational shape','Illustrative 150-column concept, invented names and counts. Existing decks and placement concepts retained.')
t=Terminal(c,48,126,150,29); chrome(t)
t.divider(61,5,27)
t.at(0,5,'@default                         5 agents',GOLD,True)
t.at(0,7,'v cache-fix             RUNNING       02m',GREEN)
t.at(2,8,'cache-fix--impl       RUNNING       local')
t.fill(0,10,60,'#2B3549'); t.at(0,10,'> schema-audit          ASKING        09m',GOLD,True)
t.at(2,11,'Needs input: approve migration strategy',GOLD)
t.at(0,13,'  tests-review          DONE unread   12m')
t.at(0,15,'  parser-cleanup        DONE read     34m',MUTED)
t.at(0,17,'v build-check           MONITOR       06m',CYAN)
t.at(2,18,'build-check--mon      command running')
t.at(64,5,'schema-audit   |   ASKING   |   local',GOLD,True)
t.at(64,7,'Main   /   Context + Reply',CYAN,True)
t.at(64,9,'CONTEXT')
t.at(64,10,'Review the schema change and propose a migration.',MUTED)
t.at(64,13,'REPLY')
t.at(64,14,'I recommend preserving both columns until backfill completes.')
t.at(64,15,'Choose a migration strategy in the review gate.')
t.at(64,19,'Links: plan:schema-rollout  ·  bead:sase-example',CYAN)
t.at(64,23,'Enter: available actions     p: Main / Files / Tools / FINAL',MUTED)
t.at(0,27,'j/k move   ,/ filter   ,a History   p deck   Ctrl+F/B focus   r refresh',MUTED)
c.lines(36,859,['Inbox includes completed work kept for review. “Live” would describe this view poorly.',
                'Switching to History parks the selected identity, filters, placement tab, folds, and deck position.'],18,MUTED,mono=False,gap=29)
c.save('02_inbox')

c=Canvas(1560,970,'03 / History is a catalog with real agent decks','Illustrative 150-column concept. Reading a dismissed run does not revive it or alter inbox counts.')
t=Terminal(c,48,126,150,30); chrome(t,True)
t.at(0,4,'Query: in:local project:sase name:parser*',GOLD)
t.divider(61,6,28)
t.at(0,6,'HISTORY  |  12 matches  |  newest activity first',CYAN,True)
t.at(0,8,'TODAY · Oct 08',MUTED,True)
t.at(0,9,'  parser-tests          DONE       inbox')
t.at(0,11,'YESTERDAY · Oct 07',MUTED,True)
t.fill(0,12,60,'#2B3549'); t.at(0,12,'> parser-cleanup        DONE       dismissed',GOLD,True)
t.at(2,13,'local · 3 turns · 11:42 · restorable',CYAN)
t.at(0,15,'  parser-retry          FAILED     dismissed',RED)
t.at(2,16,'local · 2 turns · 10:15 · restorable',MUTED)
t.at(0,18,'OLDER · Oct 04',MUTED,True)
t.at(0,19,'  parser-exploration    DONE       dismissed')
t.at(2,20,'local · reply unavailable',MUTED)
t.at(0,24,'Selection stays fixed when new rows arrive.',MUTED)
t.at(64,6,'parser-cleanup   |   DONE   |   Dismissed',GOLD,True)
t.at(64,7,'Local archive · ended Oct 07 11:42 · no runner',MUTED)
t.at(64,9,'Main / Reply   ( plan | mon | [ impl ] )',CYAN,True)
t.at(64,11,'REPLY · parser-cleanup--impl')
t.at(64,13,'Simplified the parser and preserved the error positions.')
t.at(64,14,'The targeted tests pass. The changes are ready to review.')
t.at(64,17,'Files: 2 retained diffs    Tools: retained    FINAL: retained',MUTED)
t.at(64,20,'Links: stitch:example-2  ·  plan:parser-cleanup',CYAN)
t.at(64,23,'Enter: Restore to inbox / Copy ref / Open transcript',MUTED)
t.at(64,24,'Restore changes visibility; it does not start another run.',CYAN)
t.at(0,28,'j/k move   ,/ filter   ,a Inbox   p deck   ( / ) turn   ^ prior query',MUTED)
c.lines(36,886,['No agent placement strip or tribe tree here. Dates and session groups are browsing aids.',
                'Status (DONE/FAILED), inbox presence (dismissed), and content availability remain separate facts.'],18,MUTED,mono=False,gap=29)
c.save('03_local_history')

c=Canvas(1560,970,'04 / Published history declares its evidence','Phase-two concept. Snapshot state is historical evidence, never a remote-control signal.')
t=Terminal(c,48,126,150,30); chrome(t,True,True)
t.at(0,4,'Query: in:published project:sase name:cache*',GOLD)
t.at(0,5,'Snapshot: 8c3e1a2  |  last synchronized Oct 06 09:20  |  Sync published history',CYAN)
t.divider(61,7,28)
t.at(0,7,'PUBLISHED HISTORY  |  4 matches',CYAN,True)
t.at(0,9,'OCT 06',MUTED,True)
t.fill(0,10,60,'#2B3549'); t.at(0,10,'> cache-audit           WAS ACTIVE',GOLD,True)
t.at(2,11,'published · athena · observed Oct 06 08:45',MUTED)
t.at(0,13,'  cache-fix             DONE')
t.at(2,14,'local + published · apollo',CYAN)
t.at(0,17,'One logical row per run; all source locations retained.',MUTED)
t.at(64,7,'cache-audit   |   Published snapshot',GOLD,True)
t.at(64,9,'Recorded state: ACTIVE as of Oct 06 08:45',CYAN)
t.at(64,10,'Current liveness: unknown   |   Owner: athena',MUTED)
t.at(64,12,'Main / Snapshot + Reply',CYAN,True)
t.at(64,14,'Published reply content appears here when retained.')
t.at(64,15,'A snapshot does not imply a controllable agent on this host.')
t.at(64,18,'Files: 1 published commit    Tools: not published',MUTED)
t.at(64,19,'FINAL: not published',MUTED)
t.at(64,22,'Enter: Copy ref / Open published page / Open transcript',MUTED)
t.at(64,23,'Restore unavailable: no local archive bundle.',CYAN)
t.at(0,28,'j/k move   ,/ filter   ,a Inbox   p deck   ^ prior query   Ctrl+O back',MUTED)
c.lines(36,886,['Source: This machine / Published project / Combined. Combined is not called “all agents everywhere”.',
                'Snapshot freshness, synchronization time, and a run’s observation time are different facts.'],18,MUTED,mono=False,gap=29)
c.save('04_published_history')

c=Canvas(1560,1060,'05 / Read first, restore only when useful','Storyboard. Returning to the Inbox and returning along the navigation trail are explicit choices.')
panels=[(36,130,718,355),(806,130,718,355),(36,570,718,355),(806,570,718,355)]
for x,y,w,h in panels: c.rect(x,y,w,h)
for (x,y,_,_),title in zip(panels,['1  Locate the past run','2  Read without restoring','3  Choose a visibility action','4  Return with your place intact']): c.text(x+22,y+20,title,22,GOLD,mono=False,bold=True)
c.lines(58,202,['Inbox | [ History ]','Source: This machine','in:local name:parser*','','> parser-cleanup     DONE dismissed','  parser-tests       DONE inbox'],18)
c.lines(58,395,['Only the source lens and query change.', 'No lifecycle mutation occurs.'],16,MUTED,mono=False)
c.lines(828,202,['parser-cleanup  |  Local archive','Main / Reply  [ impl ]','','“Simplified the parser…”','','Files / Tools / FINAL when retained'],18)
c.lines(828,395,['Selection loads content lazily.', 'No read/unread or runner-count side effects.'],16,MUTED,mono=False)
c.lines(58,643,['Enter > Actions','','> Restore to inbox','  Copy agent reference','  Open transcript','','Restore to inbox does not resume execution.'],18)
c.lines(58,844,['Bulk restore reports restored / skipped / failed.', 'Stay in History; offer “Show in inbox”.'],16,MUTED,mono=False)
c.lines(828,643,['[ Inbox ] | History','','Prior query: needs:input','Prior tab: main','Prior selection: schema-audit','','“parser-cleanup restored. Show in inbox”'],18)
c.lines(828,844,['Normal switch restores the parked Inbox.', 'Show in inbox deliberately reveals the restored run.'],16,MUTED,mono=False)
c.arrow(764,307,797,307); c.arrow(394,494,394,557); c.arrow(764,747,797,747)
c.lines(36,975,['A link jump creates a trail entry; Ctrl+O goes back across tabs. ^ restores the prior query.',
                'Restoration and continuation are separate actions with different effects.'],18,MUTED,mono=False,gap=29)
c.save('05_restore_storyboard')

c=Canvas(1000,1250,'06 / A 90-column terminal','Proposed compact layout. One surface at a time; no unreadable narrow split.')
t=Terminal(c,50,126,90,20)
t.at(0,0,'SASE [Agents] Artifacts Services',GOLD,True)
t.at(0,2,'Inbox | [History]   ,a switch   Source: Local',CYAN)
t.at(0,3,'in:local project:sase name:parser*',GOLD)
t.at(0,5,'HISTORY / 12 matches   Date v',CYAN,True)
t.at(0,7,'YESTERDAY · Oct 07',MUTED)
t.fill(0,8,88,'#2B3549'); t.at(0,8,'> parser-cleanup   DONE   dismissed   local',GOLD,True)
t.at(2,9,'3 turns · restorable · reply and 2 diffs retained',MUTED)
t.at(0,11,'  parser-retry     FAILED dismissed   local',RED)
t.at(2,12,'2 turns · restorable',MUTED)
t.at(0,15,'Detail preview: Simplified the parser and preserved error positions.',MUTED)
t.at(0,18,'j/k move  Ctrl+F detail  Enter actions  ,/ filter  ,a Inbox',MUTED)
c.arrow(490,626,490,676)
c.text(516,645,'Ctrl+F focuses the detail surface',16,CYAN,mono=False)
t=Terminal(c,50,710,90,19)
t.at(0,0,'SASE [Agents] Artifacts Services',GOLD,True)
t.at(0,2,'History > parser-cleanup > Main / Reply',CYAN,True)
t.at(0,3,'DONE · Dismissed · local archive · ended Oct 07 11:42',MUTED)
t.at(0,5,'Turns: plan | mon | [impl]       ( / ) previous / next',CYAN)
t.at(0,7,'REPLY')
t.at(0,9,'Simplified the parser and preserved the error positions.')
t.at(0,10,'The targeted tests pass. The changes are ready to review.')
t.at(0,13,'Links: stitch:example-2 · plan:parser-cleanup',CYAN)
t.at(0,17,'Ctrl+B list  p deck  Enter actions  ,a Inbox',MUTED)
c.text(36,1200,'The query, selected row, scroll position, and focused turn survive this view change.',17,MUTED,mono=False)
c.save('06_compact_terminal')

c=Canvas(1560,930,'07 / Honest states, useful next actions','Microcopy plate. These states are different and should not all render as “No agents found”.')
states=[
 ('A / Inbox clear',['No agents need attention.','Completed runs stay available in History.','','[ Browse history ]'],CYAN),
 ('B / Search has no matches',['No matches in this machine’s history.','Project: sase  ·  Query: name:parser*','','[ Clear name filter ]  [ Change source ]'],CYAN),
 ('C / Search is still incomplete',['Showing 50 loaded results.','Older history is still being searched.','','Searching…  Cancel preserves the current view.'],GOLD),
 ('D / Content was not retained',['Reply unavailable for this run.','Identity, timestamps, and links are still available.','','[ Copy reference ]  [ View retained files ]'],MUTED),
 ('E / Published source unavailable',['Published history could not be loaded.','This machine’s retained history is available.','','[ Use local history ]  [ Retry source ]'],RED),
 ('F / Returned row differs from selected row',['Loading the selected run’s reply…','Keep the identity header and content placeholder.','','Never show the previous agent’s text under this name.'],GOLD),
]
for i,(title,ss,color) in enumerate(states):
    x=36+(i%2)*770; y=126+(i//2)*239
    c.rect(x,y,718,213); c.text(x+21,y+19,title,20,color,mono=False,bold=True)
    c.lines(x+21,y+65,ss,16,FG,29)
c.lines(36,861,['Color is supplementary. Every condition has a text label, and each recovery action names its effect.'],18,MUTED,mono=False)
c.save('07_state_plate')

with (assets / 'generate_figures.py').open('x') as f: f.write(Path(__file__).read_text())
info={'report':str(report),'assets':str(assets),'relative_report':str(report.relative_to(ROOT)), 'asset_dirname':assets.name}
Path('/tmp/cdx_agents_ux_paths.json').write_text(json.dumps(info))
print(json.dumps(info))
print('Created 7 PNGs, 7 editable SVGs, and their generator. Report path remains unused until exclusive write.')
