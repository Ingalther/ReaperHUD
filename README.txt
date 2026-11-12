(DON'T FEAR) THE REAPER HUD  -  a red and black cyberpunk TF2 HUD
Made by Ingalther  -  version 1.0
==============================================================

Beyond the Wall (黒壁の彼方): black glass, crimson light and a broken signal, seen through the
terminals of a Japanese megacorporation.

Discord: https://discord.gg/YyzBcAAYa2

INSTALLATION
------------
1) Download the newest ZIP from https://github.com/Ingalther/ReaperHUD/releases/latest
   (or Code > Download ZIP) and extract it.
2) Put the extracted folder (ReaperHUD-main) into
   ...\steamapps\common\Team Fortress 2\tf\custom\
   resource, scripts, materials and info.vdf must sit directly inside it.
3) Remove any other HUD from custom and restart TF2.

WHAT'S IN IT
------------
- Main menu: a looping video of the Wall's circuitry behind the REAPER logo, your profile and rank,
  the friends panel, quick buttons (server browser, create server, music on / off), and its own
  menu music and startup video.
- In game: health and ammo as black glass cards either side of the crosshair, with the live class
  model as an ID photo and red and cyan glitch copies on the digits; item meters, ÜberCharge, metal
  and sticky strips, the kill streak row, teammates' slots at the top with their health and respawn
  time.
- Glitches set off by the game: near death the Blackwall breaks through the screen (with its sound),
  the ammo card flickers when low, the über strip flickers READY when full.
- Team colours: crimson on RED, azure on BLU, the whole HUD over.
- Kill feed, damage numbers, target ID (a health tag over the player you look at), killcam, win
  panel, notifications, Engineer / Spy menus, a hitmarker and directional damage arcs.
- Class select as a code matrix, a split team select, an armoury-style loadout page, and the
  backpack, crafting, scoreboard, MvM and loading screens in the same look.

HUD SETTINGS
------------
"HUD Settings" in the main menu:
- Layout: CENTRED (default) or MINMODE        (console: cl_hud_minmode 0 / 1)
- Player: 3D MODEL or 2D IMAGE                (console: cl_hud_playerclass_use_playermodel 1 / 0)
- Crosshair: six of the HUD's own, your own (MINE) or the game's (DEFAULT)
- Kill sound: six Blackwall sounds, TF2's own, or off
- Quick fixes: one click each for broken sounds, broken HUD colours and invisible players
The crosshair and the kill sound take effect through update.bat: pick, close TF2, run update.bat.

GOOD TO KNOW
------------
- Interface files only (layouts, animations, images, sounds): nothing VAC looks at. The images use
  the path sv_pure allows, so the HUD works on Valve's casual servers too.
- No fonts to install: the HUD brings its own.
- The launch option -novid skips the startup video; -nostartupsound mutes the menu music.

UPDATING
--------
With TF2 closed, run update.bat. It pulls the latest version, rebuilds the HUD from TF2's current
files and checks the install: another HUD or a mod in tf\custom that mixes its files in with this
one's is named and can be moved into tf\custom_disabled (nothing is deleted). It writes
rk_report.txt next to itself: send that along with a screenshot when you report a problem.
update.bat needs Git, Python 3, Pillow and numpy (all free) and offers to install the missing ones.

UNINSTALL
---------
Delete the HUD folder from tf\custom and restart TF2. If one of the HUD's crosshairs was picked,
type crosshair 1 in the console.

The menu music, startup video, menu video and Blackwall sounds come from Cyberpunk 2077
(CD PROJEKT RED). This is a fan-made HUD, not affiliated with CD PROJEKT RED or Valve.

Licence: CC BY-NC-SA 4.0 (see LICENSE.txt). The fonts in tools/fonts are under the SIL Open
Font License 1.1 (see tools/fonts/OFL.txt).
