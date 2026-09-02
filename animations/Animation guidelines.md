each part is representing the sprite

layer rules: each sprite have layering rules, eg how dominant it shoud be, here are the layers from most upper to the last one:
1. effects 

2\. paws 

3\. table 

4\. face
5. body



effects guidelines: 



Normal typing:
left paw down, both paws up, right paw down, both paws up

Fast typing:
add correspondick click effects, eg left click effect when left paw down



Blinking: 
randomly swap stock face with blincking face at some interwal

Typing streak:

If typing is long enough ( some set up threshold) in typing animation stock face shoud be changed with happy fave 

SHort idle: remove the hands, so its like they are underneath the table 


mid idle: while hand removed swap stock face with sleepy face 

long idel: add sleepy effect, that fill loop sleepy effect from one to three

10 min idle: swap to excited face, frantic paws, cycle excited1/excited2 sparkles until typing resumes

20 min idle: screensaver — sleepy face, paws hidden, slow Zzz, cat shrinks to 2x and drifts around the screen. First key snaps it home.

Typo tantrum: 4+ backspace/delete in 1.5s → squint (blink_face) + paws up for ~800ms. Dedicated grumpy face can replace blink_face later in sprite studio.

Save sparkle: Ctrl/Cmd+S → happy face + excited sparkles for ~400ms

Groom fidget: ~2.5s after typing animation stops (once per idle) → ear twitch body + left paw down as a lick, then resume idle

Paw modes:
Groove: host sends SPEED, firmware loops left/up/right/up
Mimic: host sends TAP:L / TAP:R per key (no SPEED). Firmware does not loop paws.

Ear twitch: randomly while idle change stock body to bodyeartwitch, stock-twicth-stock-twitch-stock

