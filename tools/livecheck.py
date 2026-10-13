from playwright.sync_api import sync_playwright
import sys
url=sys.argv[1];errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':1400,'height':900})
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.on('console',lambda m:errs.append(m.text) if m.type=='error' else None)
    pg.goto(url);pg.wait_for_timeout(800)
    print('orig cards',pg.locator('.pcard').count())
    pg.click('#tabComm');pg.wait_for_timeout(200)
    print('comm cards',pg.locator('.pcard').count())
    
    pg.click('.pcard .t');pg.wait_for_timeout(400)
    pg.keyboard.type('SUB')
    print('title',pg.inner_text('#puzTitle'),'|',pg.inner_text('#puzLic'))
    b.close()
print('ERRORS',errs)
