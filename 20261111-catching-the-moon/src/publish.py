"""Stage a version into the showroom repo folder (no git operations here).
usage: python publish.py <film.mp4> <label> <poster_time_s>"""
import sys, os, shutil, subprocess, hashlib, json
film, label, pt = sys.argv[1], sys.argv[2], float(sys.argv[3])
HERE = os.path.dirname(os.path.abspath(__file__))
MOTH = os.path.abspath(os.path.join(HERE, '..'))
REPO = '/home/pmli/workspace/_repo/claude-showroom'
SLUG = '20261111-catching-the-moon'
DST = os.path.join(REPO, SLUG)
os.makedirs(os.path.join(DST, 'shots'), exist_ok=True)
os.makedirs(os.path.join(DST, 'src'), exist_ok=True)

shutil.copy2(film, os.path.join(DST, 'film.mp4'))
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(pt), '-i', film, '-frames:v', '1', '-q:v', '3', os.path.join(DST, 'poster.jpg')], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(pt), '-i', film, '-frames:v', '1', '-vf', 'scale=640:-1', '-q:v', '4',
                os.path.join(DST, 'shots', 'thumb.jpg')], check=True)
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', film], capture_output=True, text=True).stdout)
sha = hashlib.sha256(open(film, 'rb').read()).hexdigest()

about = open(os.path.join(MOTH, 'site', 'about.html')).read()
html = open(os.path.join(MOTH, 'site', 'index.html')).read()
html = html.replace('__DUR__', f'{int(dur // 60)}:{int(round(dur % 60)):02d}').replace('__ABOUT__', about).replace('__VERSION__', label)
open(os.path.join(DST, 'index.html'), 'w').write(html)
shutil.copy2(os.path.join(MOTH, 'site', 'README.md'), os.path.join(DST, 'README.md'))
open(os.path.join(DST, 'VERSION.txt'), 'w').write(f'{label}\nduration {dur:.2f} s\nsha256 {sha}\n')
for fn in ('engine.py', 'puppets.py', 'film.py', 'audio.py', 'render.py', 'master.sh', 'check_sync.py', 'publish.py'):
    shutil.copy2(os.path.join(HERE, fn), os.path.join(DST, 'src', fn))

# root index card + README row (insert once)
idx = os.path.join(REPO, 'index.html')
s = open(idx).read()
if SLUG not in s:
    card = f'''    <article class="card">
      <a class="thumb" href="{SLUG}/" style="background-image:url('{SLUG}/shots/thumb.jpg')" aria-label="Catching the Moon film"></a>
      <div class="body">
        <div class="date">2026-11-11 · {SLUG}</div>
        <h2 class="title">撈月<small>Catching the Moon</small></h2>
        <p class="desc">一齣沒有台詞的皮影戲：一個想要月亮的老漁夫。<small>A wordless shadow play about an old fisherman who wants the moon.</small></p>
        <div class="links">
          <a class="btn primary" href="{SLUG}/">▶ 觀看 Watch</a>
          <a class="btn" href="https://github.com/TheDreamersTop/claude-showroom/tree/main/{SLUG}">原始碼 Source</a>
        </div>
      </div>
    </article>
'''
    anchor = '  </main>'
    assert s.count(anchor) == 1
    s = s.replace(anchor, card + anchor)
    open(idx, 'w').write(s)
rd = os.path.join(REPO, 'README.md')
s = open(rd).read()
if SLUG not in s:
    row = (f'| 2026-11-11 | 撈月 Catching the Moon | 一齣沒有台詞的皮影戲，全部用程式算出來：一個想要月亮的老漁夫，和戲台後面一隻真的飛蛾。'
           f'<br/>*A wordless shadow play rendered entirely in code: an old fisherman who wants the moon, and a real moth behind the screen.* '
           f'| [▶ Watch](https://thedreamerstop.github.io/claude-showroom/{SLUG}/) | [`{SLUG}/`]({SLUG}/) |\n')
    marker = '| 2026-11-10 | 還在冒泡'
    i = s.index(marker)
    j = s.index('\n', i) + 1
    s = s[:j] + row + s[j:]
    open(rd, 'w').write(s)
print(json.dumps({'dst': DST, 'duration': round(dur, 2), 'sha256': sha, 'bytes': os.path.getsize(film)}))
