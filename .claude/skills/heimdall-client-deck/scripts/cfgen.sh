#!/bin/zsh
# usage: cfgen.sh name "prompt"  (flux-1-schnell via Workers AI; 1024x1024 default -> we ask 16:9 via width/height)
source ~/.zshrc >/dev/null 2>&1
W=${3:-1344}; H=${4:-768}
curl -s -m 180 "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/ai/run/@cf/black-forest-labs/flux-1-schnell" -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" -H 'content-type: application/json' \
  -d "$(python3 -c "import json,sys; print(json.dumps({'prompt': sys.argv[1], 'steps': 8}))" "$2" "$W" "$H")" -o "$1.json"
python3 -c "
import json,base64,sys; d=json.load(open('$1.json')); img=(d.get('result') or {}).get('image')
open('$1.png','wb').write(base64.b64decode(img)) if img else print('FAIL', d.get('errors'))
print('$1', 'ok' if img else 'fail')"
