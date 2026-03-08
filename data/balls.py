# https://github.com/yang-ch92o/Lottery
import Box2D as box2d
import sys, os, traceback
import random
import time
import tomllib
import secrets
import math
sys.path.append(os.path.dirname(__file__))
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
try:
	from  _lottery_data import *
except ImportError:
	class DEFAULT_CONFIG:BALLS={}


join=os.path.join
dir=os.path.dirname(__file__)

class Ball:
	def __init__(
			self, world: box2d.b2World, x, y, r=1, 
			density=1,restitution=.5,friction=0.3,color=(255,0,0),**tag
		):
		self.world = world
		self.body = world.CreateDynamicBody(position=(x, y), angle=0.1)
		self.body.CreateCircleFixture(
			radius=r, density=density,restitution=restitution,friction=friction
		)
		self.position = self.body.position
		self.r = r
		self.color = color
		self.isholding=False
		self.holdoffset=(0,0)
		if tag is None:self.tag={}
		else:self.tag=tag
	def draw(self, screen:pygame.Surface,scale=10):
		pygame.draw.circle(
			screen, self.color, 
			(self.body.position[0]*scale,self.body.position[1]*scale), self.r*scale
		)
def input_intergral(rect,max_val=10):
	inp=''
	numkeys=[pygame.K_0,pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4,pygame.K_5,pygame.K_6,pygame.K_7,pygame.K_8,pygame.K_9]
	font = pygame.font.Font(None, 32)
	scr=pygame.Surface((rect[2],rect[3]))
	while True:
		for event in pygame.event.get():
			if event.type == pygame.KEYDOWN:
				if event.key in numkeys:
					inp+=str(numkeys.index(event.key))
					if int(inp)>max_val:
						inp=inp[:-1]
				elif event.key == pygame.K_BACKSPACE:
					inp=inp[:-1]
				elif event.key == pygame.K_RETURN:
					if inp:return int(inp)
					else:return 0
				elif event.key in {pygame.K_ESCAPE,pygame.K_q}:
					return 0
			elif event.type==pygame.QUIT:
				return 0
		scr.fill((255,255,255))
		text=font.render(inp,True,(0,0,0))
		scr.blit(text,(0,0))
		pygame.display.get_surface().blit(scr,(rect[0],rect[1]))
		pygame.display.update(rect)
message=\
'''\
[S]     Start
[F]     Shake
[R]     Reset
[O]     Open/Close Hole
[Enter] Show Winners
[Q]     Quit
'''

pygame.font.init()
pygame.init()

def random_string(length=10):
	c=0
	skip=[(0xd800,0xdfff),(0,31),(0xe000,0xf8ff),(0x1780,0x1c7f),(0xfff0,0xffff),(0xfb00,0xfdff),(0xa800,0xabff),(0xac00,0xd7ff)]
	ch=''
	while c<length:
		n=random.randint(0,0xffff)
		for i in skip:
			if i[0]<=n<=i[1]:
				break
		else:
			c+=1
			ch+=chr(n)
		
	return ch
def main(gcfgf=None,cfgf=None,membercfg=None):
	def load(gc:str=None,c:str=None,mc:str=None):
		if gc is None:
			gc='config.toml'
		if c is None:
			c='balls.toml'
		nonlocal all_names,cfg,fontpath,ballfont,gconfig
		all_names=[]
		gconfig = tomllib.load(open(join(dir,gc),'rb'))
		cfg=DEFAULT_CONFIG.BALLS|tomllib.load(open(join(dir,c),'rb'))
		fontpath=join(dir,gconfig['font'])
		ballfont=pygame.font.Font(fontpath,int(cfg['font-size']*cfg['scale']))
		if mc is None:mc='members.toml'
		v=tomllib.load(open(join(dir,mc),'rb'))
		for i in v['number']:
			if i not in v['disabled']:
				for _ in range(v['number'][i]):
					all_names.append(i)
		del v
	all_names:list[str]
	cfg:dict
	fontpath:str
	ballfont:pygame.font.Font
	gconfig:dict
	load(gcfgf,cfgf,membercfg) # 加载配置文件
	SCALE=cfg['scale']
	UISCALE=cfg['ui-scale']
	Fingers={-1:[0,0,math.inf,{'fake'},-1,0]}
	class ToolbarButton:
		x:int
		w:int
		r:pygame.Rect
		cm:bool
		def __init__(self,text,func,color="#1C396C",pressed_color="#254C91"):
			self.text=text
			self.func=func
			self.color=color
			self.pressed_color=pressed_color
		def get_text(self):
			return self.text
	def rf():
		random_force((-cfg['force'],cfg['force']),(-cfg['force'],cfg['force']))
	def create_new_ball(pos=None,force=None,**tags):
		if pos is None:
			w,h=pygame.display.get_surface().get_size()
			pos=(w/2+random.randint(-200,200)/3,h/2+random.randint(-200,200)/3)
		color=random.choice(cfg['dark-ball-colors']+cfg['light-ball-colors'])
		if color in cfg['dark-ball-colors']:
			fg=cfg['dark-ball-fg']
		else:
			fg=cfg['light-ball-fg']
		items.append(Ball(world,pos[0]/SCALE,pos[1]/SCALE,density=cfg['ball-density'],restitution=cfg['ball-restitution'],friction=cfg['ball-friction'],color=color,fg=fg,**tags))
		if force is None:
			force=(random.randint(-1000,1000),random.randint(-2000,500))
		items[-1].body.ApplyForce(force,items[-1].body.worldCenter,True)
	def init_world(*_):
		nonlocal randomforcetime,openhole,show_title,extend
		extend=0
		show_title=False
		openhole=False
		randomforcetime=0
		for i in items:
			world.DestroyBody(i.body)
		items.clear()
		n=0
		l=all_names.copy()
		random.seed(secrets.token_bytes(16))
		random.shuffle(l)
		for i in range(len(l)):
			create_new_ball(r=cfg['ball-r'],id=n)
			n+=1
		random_force((-cfg['initial-force'],cfg['initial-force']),(-cfg['initial-force'],cfg['initial-force']))
	def shake(s:ToolbarButton=None):
		nonlocal randomforcetime
		if randomforcetime<=0:
			randomforcetime=cfg.get('shake-time',240)
		else:
			randomforcetime=0
		# if s is not None:
		# 	s.text=['停止摇晃','开始摇晃'][randomforcetime>0]

	def open_or_close_hole(s:ToolbarButton=None):
		nonlocal openhole
		openhole=not openhole
	def show_or_hide_title(s:ToolbarButton=None):
		nonlocal show_title,title
		show_title=not show_title
		if show_title:
			title=rend_title()
	def rend_title():
		if len(winners_names)==0:n=cfg['win-text']%cfg['nobody']
		else:
			n=list(set(winners_names))
			n.sort()
			n=cfg['win-text']%(cfg['winner-sep'].join(n))
		try:
			title=titlefont.render(n,True,cfg['title-fg'],cfg['title-bg'],ws-cfg['title-edge']*2)
		except:
			traceback.print_exc()
			title=titlefont.render(n,True,cfg['title-fg'],cfg['title-bg'])
		return title
	def 掀起():
		for i in items:
			i.body.ApplyForce((0,-cfg['force']/1.5),i.body.worldCenter,True)
	def random_force(rangex=(-10000,10000),rangey=(-10000,10000)):
		'给予每个球随机力'
		for i in items:
			i.body.ApplyForce((random.randint(*rangex),random.randint(*rangey)),i.body.worldCenter,True)
	world = box2d.b2World((0,cfg['gravity']))
	items:list[Ball]=[]
	uicfg={'toolbar-height':26,'toolbar-bg':"#202020"}
	os.chdir(dir)
	# print(os.getcwd())
	# print(message)
	window = pygame.display.set_mode(cfg['default-resoulution'],pygame.DOUBLEBUF|pygame.RESIZABLE)
	pygame.display.set_icon(pygame.image.load(join(dir,cfg['icon'])))
	g=world.CreateStaticBody(position=(0, 0))
	pygame.display.set_caption("Lottery - Balls")
	pygame.key.stop_text_input()
	t=0
	clock=pygame.time.Clock()
	speed=2.0
	init_world()
	randomforcetime=0
	show_title=False
	extend=0
	ballimg=[pygame.transform.scale,pygame.transform.smoothscale][int(cfg['ball-smooth'])](pygame.image.load(join(dir,cfg['ball-image'])),(cfg['ball-r']*20,cfg['ball-r']*20))
	if cfg['ball-onecolor']:
		ballimg.fill('white',None,pygame.BLEND_RGB_ADD)
	openhole=False
	show_title=False
	titlefont=pygame.font.Font(fontpath, int(cfg['title-font-size']*UISCALE))
	toolbartools=[ToolbarButton('开始摇晃',shake),ToolbarButton('重置',init_world),ToolbarButton('打开洞',open_or_close_hole),ToolbarButton('显示获奖名单',show_or_hide_title),ToolbarButton('摇晃',rf),ToolbarButton('掀起',掀起),ToolbarButton('退出',sys.exit,"#9c0000","#f40000")]
	tbfont:pygame.font.Font=pygame.font.Font(fontpath,int((uicfg['toolbar-height']-10)*UISCALE))
	toolbartools[0].get_text=lambda:['停止摇晃','开始摇晃'][randomforcetime<=0]
	toolbartools[2].get_text=lambda:['打开洞','关闭洞'][openhole]
	winners=[]
	winners_names=[]
	if cfg['bg-img']:
		bgimg=pygame.image.load(join(dir,cfg['bg-img'])).convert()
	else:
		bgimg=None
	for i in items:
		get_name=lambda i:all_names[i.tag.get('id',0)] if cfg['floor-y'] else str(i.tag.get('id',float('nan'))+1).replace('nan','?')
	while True:
		TOOLBAR_REAL_HEIGHT=uicfg['toolbar-height']*UISCALE
		ws,hs=pygame.display.get_surface().get_size()
		rw,rh=ws,hs
		hs-=TOOLBAR_REAL_HEIGHT
		screen=pygame.Surface((ws,hs))
		w=ws/SCALE
		h=hs/SCALE
		randomforcetime-=1
		if randomforcetime>=0 and randomforcetime%2==0:
			rf()
			if randomforcetime==0:
				openhole=True
			# 	toolbartools[0].text='开始摇晃'
			# else:
			# 	toolbartools[0].text='停止摇晃'
		toolbarimg=pygame.Surface((ws,TOOLBAR_REAL_HEIGHT),)
		toolbarimg.fill(uicfg['toolbar-bg'])
		_tbx=6
		_pa=10
		for i in toolbartools:
			text=tbfont.render(i.get_text(),True,'white')
			i.x=_tbx-_pa/2*UISCALE
			i.w=text.get_width()+_pa*UISCALE
			i.r=pygame.Rect(i.x,0,i.w,TOOLBAR_REAL_HEIGHT)
			_tbx+=text.get_width()+_pa*UISCALE
			if i.r.collidepoint(pygame.mouse.get_pos()):
				i.cm=1
				toolbarimg.fill(i.pressed_color if pygame.mouse.get_pressed()[0] else i.color,i.r)
			else:
				i.cm=0
			toolbarimg.blit(text,(i.x+_pa/2*UISCALE,0))
		events=pygame.event.get()
		mousepos=pygame.mouse.get_pos()
		mouseposinstage=mousepos[0]/SCALE,(mousepos[1]-TOOLBAR_REAL_HEIGHT)/SCALE
		for event in events:
			if event.type == pygame.QUIT:
				sys.exit()
			elif event.type == pygame.KEYDOWN:
				match event.key:
					case pygame.K_SPACE:
						掀起()
					case pygame.K_s:
						shake()
					case pygame.K_p:
						randomforcetime=0
					case pygame.K_f:
						random_force((-cfg['force'],cfg['force']),(-cfg['force'],cfg['force']))
					case pygame.K_r:
						init_world()
					case pygame.K_o:
						openhole=not openhole
					case pygame.K_RIGHT:
						extend+=1
					case pygame.K_LEFT:
						extend-=1
						if extend<0:extend=0
					case pygame.K_F11:
						pygame.display.toggle_fullscreen()
					case pygame.K_RETURN:
						if len(winners)>0:
							show_title=True
							title=rend_title()
							print(cfg['win-text']%(cfg['winner-sep'].join(winners_names)))
						else:
							show_title=False
					case pygame.K_q:
						sys.exit()
					case pygame.K_EQUALS:
						speed*=2
						speed=min(8192.0,speed)
						print('Speed: %.2fx'%speed)
					case pygame.K_MINUS:
						speed/=2
						speed=max(1/64,speed)
						print('Speed: %.2fx'%speed)
					# case _:
					# 	create_new_ball()
			elif event.type == pygame.MOUSEBUTTONUP:
				if event.button==pygame.BUTTON_LEFT:
					if pygame.mouse.get_pos()[1]<TOOLBAR_REAL_HEIGHT:
						for i in toolbartools:
							if i.cm:
								i.func()
					for i in items:
						i.isholding=False
				elif event.button==pygame.BUTTON_RIGHT:
					for i in items:
						if i.tag.get('is-target',False):
							if i.tag.get('is-target-finger',None) is None:
								i.body.ApplyForce(((mouseposinstage[0]-i.body.position[0])*cfg['throw-strength'],(mouseposinstage[1]-i.body.position[1])*cfg['throw-strength']),i.body.worldCenter,True)
								i.tag['is-target']=False
			elif event.type == pygame.MOUSEBUTTONDOWN:
				for i in items:
					if (i.body.position[0]-mouseposinstage[0])**2+(i.body.position[1]-mouseposinstage[1])**2<i.r**2:
						if event.button==pygame.BUTTON_LEFT:
							i.isholding=True
							i.holdoffset=(mouseposinstage[0]-i.body.position[0],mouseposinstage[1]-i.body.position[1])
							print('Holding: %s (%i)'%(get_name(i),i.tag.get('id',0)))
						elif event.button==pygame.BUTTON_RIGHT:
							i.tag['is-target']=True
							print('Target Set: %s (%i)'%(get_name(i),i.tag.get('id',0)))
			elif gconfig['touchscreen']:
				if event.type == pygame.FINGERDOWN:
					Fingers[event.finger_id]=[event.x*rw,event.y*rh,time.time(),set(),0,0]
					print('Finger Down: %i'%event.finger_id)
				elif event.type == pygame.FINGERUP:
					if event.finger_id in Fingers:
						Fingers[event.finger_id][5]=1
				elif event.type == pygame.FINGERMOTION:
					if event.finger_id in Fingers:
						Fingers[event.finger_id][0],Fingers[event.finger_id][1]=event.x*rw,event.y*rh
						Fingers[event.finger_id][4]+=1
		if gconfig['touchscreen']:
			_delF=[]
			for i in Fingers:
				if Fingers[i][5]:
					Fingers[i][5]+=1
					if Fingers[i][5]>300:
						_delF.append(i)
				else:
					if not (Fingers[i][4]>2 or 'right' in Fingers[i][3]) and time.time()-Fingers[i][2]>=.5:
						Fingers[i][3].add('right')
						print('Finger Right: %i'%i)
						for j in items:
							if (j.body.position[0]-Fingers[i][0]/SCALE)**2+(j.body.position[1]-(Fingers[i][1]-TOOLBAR_REAL_HEIGHT)/SCALE)**2<=j.r**2:
								j.tag['is-target']=True
								j.tag['is-target-finger']=i
								j.isholding=False
								print('Target Set: %s (%i) (Finger)'%(get_name(j),j.tag.get('id',0)))
			for i in _delF:
				del Fingers[i]
		for i in g.fixtures:
			g.DestroyFixture(i)
		_holedepth=cfg['hole-depth']
		floor_y=cfg['floor-y']
		_space=cfg['hole-space']
		_w=cfg['ball-r']*(extend+1)
		_slopetop=-cfg['slope']*w/2+h-floor_y
		ceiling=0
		_topextent=999
		l=[
			[(0,_slopetop), (w/2-(_w+_space),h-floor_y),True], # 地面左
			[(w/2+(_w+_space),h-floor_y), (w,_slopetop),True], # 地面右
			[(0,ceiling), (w,ceiling)], # 天花板
			[(0,h), (0,ceiling-_topextent)], # 左墙
			[(w,h), (w,ceiling-_topextent)], # 右墙
			[(w/2-(_w+_space),h-floor_y), (w/2-(_w+_space),h-floor_y+_holedepth),True], # 坑左墙
			[(w/2+(_w+_space),h-floor_y), (w/2+(_w+_space),h-floor_y+_holedepth),True], # 坑右墙
			[(w/2-(_w+_space),h-floor_y+_holedepth), (w/2+(_w+_space),h-floor_y+_holedepth),True], # 坑底
		]
		if not openhole:
			l.append([(w/2-(_w+_space),h-floor_y), (w/2+(_w+_space),h-floor_y),True])

		# (255, 160, 160)
		screen.fill(cfg['bg'])  # 填充背景
		if bgimg:
			screen.blit(pygame.transform.smoothscale(bgimg,(ws,hs)),(0,0))
		# world.Step(1/60, 6, 2)
		for i in l:
			if len(i)>2:
				pygame.draw.line(screen,cfg['edge-color'],(i[0][0]*SCALE+cfg['edge-offset'][0],i[0][1]*SCALE+cfg['edge-offset'][1]),(i[1][0]*SCALE+cfg['edge-offset'][0],i[1][1]*SCALE+cfg['edge-offset'][1]),cfg['edge-width'])
			g.CreateEdgeFixture(vertices=[i[0],i[1]])
		winners=[]
		winners_names=[]
		for i in items:
			if cfg['ball-useimg']:
				b=ballimg.copy()
				b.fill(i.color,None,pygame.BLEND_MULT)
				screen.blit(b,(i.body.position[0]*SCALE-cfg['ball-r']*SCALE,i.body.position[1]*SCALE-cfg['ball-r']*SCALE))
			else:
				i.draw(screen,SCALE)  # 渲染场景
			match str(cfg['ball-text-type']).lower():
				case 'number':
					text=str(i.tag.get('id',-1)+1)
				case 'same':
					text=cfg['samename']
				case 'name':
					text=all_names[i.tag.get('id',0)] if cfg['floor-y'] else str(i.tag.get('id',float('nan'))+1).replace('nan','?')
				case 'random':
					text=random_string(random.randint(3,8))
				case typ:
					text=str(typ)
			try:
				f=ballfont.render(text,cfg['ball-text-antialias'],i.tag.get('fg','#ff00ff'))
			except:
				f=pygame.Surface((1,1),pygame.SRCALPHA)
			screen.blit(f,(i.body.position[0]*SCALE-f.get_width()/2+cfg['text-offset'][0],i.body.position[1]*SCALE-f.get_height()/2+cfg['text-offset'][1]))

			if i.body.position[1]>(h-cfg['floor-y']):
				winners.append(i.tag.get('id',0))
				winners_names.append(all_names[i.tag.get('id',0)])
			if i.isholding:
				i.body.position=(mouseposinstage[0]-i.holdoffset[0],mouseposinstage[1]-i.holdoffset[1])
				i.body.linearVelocity=(0,0)
		for i in items:
			if i.tag.get('is-target',False):
				if i.tag.get('is-target-finger',None) is not None:
					p=Fingers[i.tag.get('is-target-finger',-1)][0],Fingers[i.tag.get('is-target-finger',-1)][1]-TOOLBAR_REAL_HEIGHT
					if Fingers[i.tag.get('is-target-finger',-1)][5]:
						i.tag['is-target']=False
						del i.tag['is-target-finger']
						i.body.ApplyForce(((mouseposinstage[0]-i.body.position[0])*cfg['throw-strength'],(mouseposinstage[1]-i.body.position[1])*cfg['throw-strength']),i.body.worldCenter,True)
						p=(i.body.position[0]*SCALE,i.body.position[1]*SCALE)
				else:
					p=(mousepos[0],mousepos[1]-TOOLBAR_REAL_HEIGHT)
				pygame.draw.line(screen,cfg['target-direction-line'][0],(i.body.position[0]*SCALE,i.body.position[1]*SCALE),p,cfg['target-direction-line'][1])
		if show_title:
			try:
				tw,th=title.get_size()
				screen.blit(title,(ws/2-tw/2+cfg['title-offset'][0],hs/2-th/2+cfg['title-offset'][1]))
			except:pass
		window.blit(screen,(0,TOOLBAR_REAL_HEIGHT))
		# window.fill('#121212',(0,0,ws,TOOLBAR_REAL_HEIGHT))
		window.blit(toolbarimg,(0,0))
		pygame.display.update()
		for _ in range(max(1,int(speed))):world.Step(1/60, 6, 2)  # 更新物理世界
		clock.tick(60*min(1,speed))  # 控制帧率
		pygame.display.set_caption("Lottery - Balls | FPS: %1.1f"%clock.get_fps())
		t+=1


if __name__=='__main__':
	import sys, argparse
	parser = argparse.ArgumentParser(description='Balls Lottery')
	parser.add_argument('-c','--config',default='balls.toml',help='config file')
	parser.add_argument('-mc','--members',default='members.toml',help='member config file')
	parser.add_argument('-gc','--globalconfig',default='config.toml',help='global config file')
	args = parser.parse_args()

	main(args.globalconfig,args.config,args.members)