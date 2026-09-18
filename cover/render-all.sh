set -e
cd /tmp/claude-0/-home-user-theduppp/345eda9b-761e-5f75-ac4f-d67073835841/scratchpad/bl
S=128
python3 build.py --view portrait  --theme dark  --w 630  --h 891 --samples $S --out out/front-dark.png
python3 build.py --view portrait  --theme light --w 630  --h 891 --samples $S --out out/front-light.png
python3 build.py --view structure --theme dark  --w 1305 --h 560 --samples $S --out out/structure.png
python3 build.py --view spread    --theme dark  --w 1305 --h 891 --samples $S --out out/spread-dark.png
python3 build.py --view spread    --theme light --w 1305 --h 891 --samples $S --out out/spread-light.png
echo ALLDONE
