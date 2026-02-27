import sys, os, json, urllib.request
sys.path.insert(0, '/opt/tvi-bee')
os.chdir('/opt/tvi-bee')
from dotenv import load_dotenv
load_dotenv('/opt/tvi-bee/.env')
from api import _rough_project_query, _search_candidates, _normalize_sr, _build_prompt

n = _normalize_sr('od 8 do 13 projekat dalibor servis komentar testiranje')
r = _rough_project_query(n)
c = _search_candidates(r)
pr = _build_prompt(c)

print("Top kandidati:")
for x in c[:5]:
    print(" ", x['activity_number'], x['name'])

url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
model = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
p = json.dumps({'model': model, 'prompt': pr + '\n\nKomanda: ' + n,
                'stream': False, 'format': 'json', 'keep_alive': '10m'}).encode()
req = urllib.request.Request(url + '/api/generate', data=p,
                             headers={'Content-Type': 'application/json'})
resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
print("LLM odgovor:", resp['response'])
