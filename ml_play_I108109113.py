"""
The template of the script for the machine learning process in game pingpong
"""
import sys
import math
import csv
import numpy as np
import matplotlib.pyplot as plt

import paho.mqtt.client as mqtt
import random
import json  
import datetime 
import time
import threading
import queue

class Point:
    def __init__(self):
        self.x=None
        self.y=None
    def __init__(self,x,y):
        self.x=x
        self.y=y
    def get_dis_xy(self,p1,p2):
        p = Point()
        p.x = p2.x-p1.x
        p.y = p2.y-p1.y
        return p
class Line:
    def __init__(self):
        self.a=None
        self.b=None
        self.p1=Point()
        self.p2=Point()
        
    def get_func_r(self,p1,dp):
        if dp.x == 0:
            self.p1.x = p1.x
        if dp.y == 0:
            self.p1.y = p1.y
        if dp.x != 0 and dp.y != 0:
            self.a = dp.y/dp.x
            self.b = p1.y - self.a * p1.x
            
    def get_func_p(self,p1,p2):
        dp = Point.get_dis_xy(self, p1, p2)
        self.get_func_r(p1, dp)
    def get_cross(self,l1,l2):
        return 0
class Cross:
    def __init__(self):
        self.pos=Point()
        self.inv = None
    
class Collision:
    def __init__(self):
        self.index=0
        self.iscollision=False
        self.invertx=False
        self.inverty=False
        self.pos=Point()
        self.line=Line()
        self.dis=0
    def updata(self,pos,vel):
        bl = Line(pos,vel)
        
        
        
class Sensor:
    def __init__(self):
        self.balls_pos=[]
        self.balls_vel=[]
        self.Lines=[]
        
        
class MLPlay:
    def __init__(self, side):
        """
        Constructor

        @param side A string "1P" or "2P" indicates that the `MLPlay` is used by
               which side.
        """
        self.ball_served = False
        self.side = side
        self.ballpos =[]
        self.ballvel =[]
        self.blocker =[]
        self.blockervel =[]
        self.data =[]
        
        # 設置日期時間的格式
        self.ISOTIMEFORMAT = '%m/%d %H:%M:%S'
        
        # # 連線設定
        # # 初始化地端程式
        # self.client = mqtt.Client()
        
        # # 設定登入帳號密碼
        # self.client.username_pw_set("try","1234")
        
        # # 設定連線資訊(IP, Port, 連線時間)
        # self.client.connect("localhost", 1883, 60)
        # self.millis = int(round(time.time() * 1000))
        # self.tick = 0
        # self.Timeout = 100
        self.first =220
        self.isfirstsearch=True
        self.q = queue.Queue() 

    def update(self, scene_info):
        """
        Generate the command according to the received scene information
        """
        
        #self.tick =int(round(time.time() * 1000)) - self.millis
        
        if scene_info["status"] != "GAME_ALIVE":
            # 開啟輸出的 CSV 檔案
            name ='_' + self.side + 'logs.csv'
            with open(name, 'w', newline='') as csvfile:
                # 建立 CSV 檔寫入器
                writer = csv.writer(csvfile)
                # 寫入一列資料
                writer.writerow(['序列','狀態','玩家','命令', '板1x','板1y','板2x','板2y', '球x','球y','球速x','球速y','障礙物x','障礙物y', '預測X', '預測Y'])
                lens =len(self.data)
                for i in range(lens):
                    writer.writerow(self.data[i])
            self.reset()
            return "RESET"
        
        #nball = self.GetCenter(scene_info["ball"],(5,5))     #得到球的中心座標
        ball = self.GetCenter(scene_info["ball"],(5,5))     #得到球的中心座標
        
        if self.side =='1P':
            real = self.GetCenter(scene_info["platform_1P"],(40,30))#得到板子的中心座標
        if self.side =='2P':
            real = self.GetCenter(scene_info["platform_2P"],(40,30))#得到板子的中心座標
        
        forms= []
        forms.append( self.GetBound(pos=(2.5,2.5),size=(195,395+20),top_shift=(0,50+30)))
        ca_forms= []
        ca_forms.append( self.GetBound(pos=(2.5,2.5),size=(195,395+20),top_shift=(0,50+30)))
        ci_forms= []
        ci_forms.append( self.GetBound(pos=(2.5,2.5),size=(195,395+20),top_shift=(0,50+30)))
        if len(self.ballvel)>=1: 
            speed = scene_info["ball_speed"]
            ca_speed = scene_info["ball_speed"]
            ci_speed = scene_info["ball_speed"]
        else:
            if self.side =='1P':
                speed =(-7,-7) #初始假設的球速
                ca_speed =(-7,-7) #初始假設的球速
                ci_speed =(-7,-7) #初始假設的球速
            if self.side =='2P':
                speed =(7,7) #初始假設的球速
                ca_speed =(7,7) #初始假設的球速
                ci_speed =(7,7) #初始假設的球速
        
        
        
        bricks =[]
        bricksvel =[]
        if "blocker" in scene_info.keys():
            bricks.append(self.GetBound(pos=scene_info["blocker"],size=(30,20)))    #得到軟磚膨脹的邊界
            self.blocker.append(bricks[0])
        
        if len(self.blocker)>1:
            bricksvel.append((self.blocker[-1][0][0]-self.blocker[-2][0][0],0))
            self.blockervel.append(bricksvel[0])
        
        #------------------------------主要  初始化---------------------------------
        runframe =round(670/7) 
        #搜尋球的落點直到Timeout或找到落點
        #不切球
        balls=[]                
        balls.append(ball)
        #切快球
        cutaddball = ball
        cutaddballs=[]
        cutaddballs.append(ball)
        #切反彈球
        cutinvball = ball
        cutinvballs=[]
        cutinvballs.append(ball)
        prebricks=[]
        if len(bricks)>0:
            prebricks.append(bricks[-1][0])
        
        ca_prebricks=[]
        if len(bricks)>0:
            ca_prebricks.append(bricks[-1][0])
        
        ci_prebricks=[]
        if len(bricks)>0:
            ci_prebricks.append(bricks[-1][0])
        
        #------------------------------主要  演算---------------------------------
        #開局演算
        if (not self.ball_served) : #是開局方 且是 還沒開球時 且是 EASY 才演
            if self.side =='1P' and ball[1]>350 and self.isfirstsearch==True:
                
                t = threading.Thread(target = self.firstsearch1p,args =(forms, bricks, bricksvel, prebricks))
                t.start()
                self.isfirstsearch=False
                #self.first =45
                
            elif self.side =='2P' and ball[1]<150 and self.isfirstsearch==True:
                t = threading.Thread(target = self.firstsearch2p,args =(forms, bricks, bricksvel, prebricks))
                t.start()
                self.isfirstsearch=False
                #self.first =45
            
        else:
            # 不切球   N : None
            # 切快球   S : Supper
            # 切反彈球 I : Invert
            ball,balls,prebricks,runframe,speed = self.Ball_path_computer(ball, speed, forms, bricks, bricksvel, balls, prebricks,action = 'N')
            cutaddball,cutaddballs,ca_prebricks,runframe,ca_speed = self.Ball_path_computer(cutaddball, ca_speed,ca_forms , bricks, bricksvel, cutaddballs, ca_prebricks,action = 'S')                                                     
            cutinvball,cutinvballs,ci_prebricks,runframe,ci_speed = self.Ball_path_computer(cutinvball, ci_speed, ci_forms, bricks, bricksvel, cutinvballs, ci_prebricks,action = 'I')
            
            
        
        
        
        #------------------------------主要  End---------------------------------
        pres =[ball[0],cutaddball[0],cutinvball[0]]
        maxpos =max(pres)
        minpos =min(pres)
        mix = (maxpos + minpos)/2
        Error = mix - real[0]         #追隨誤差  值越大要右移，越小要左移 
        
        margin = 0.5
        gip=0.5
        # if self.side =='1P':
        #     L0 = 420
        #     L1 = 415
        #     L2 = 410
        # if self.side =='2P':
        #     LO = 50
        #     L1 = 55
        #     L2 = 60
        result =[]
        while not self.q.empty():
            result.append(self.q.get()) 
        
        for item in result: 
            #self.first = item[0]
            if item[1] == self.firstsearch1p.__name__: 
                self.first = item[0]
            if item[1] == self.firstsearch2p.__name__: 
                self.first = item[0]
        
        if not self.ball_served:          #還沒開球時
            if self.side=='1P':
                if ball[1]<350:
                    self.ball_served = True
                    if Error > gip:
                        command = "MOVE_RIGHT"
                    elif Error < -gip:
                        command = "MOVE_LEFT"
                    else:
                        command = "NONE"
                else:
                    if self.first!=220:
                        Error =self.first-real[0]
                        if Error > 2.5:
                            command = "MOVE_RIGHT"
                        elif Error < -2.5:
                            command = "MOVE_LEFT"
                        else:
                            self.ball_served = True
                            command = "SERVE_TO_LEFT"
                    else:
                        command = "NONE"
            elif self.side=='2P':
                if ball[1]>150:
                    self.ball_served = True
                    if Error > gip:
                        command = "MOVE_RIGHT"
                    elif Error < -gip:
                        command = "MOVE_LEFT"
                    else:
                        command = "NONE"
                else:
                    if self.first!=220:
                        Error =self.first-real[0]
                        if Error > 2.5:
                            command = "MOVE_RIGHT"
                        elif Error < -2.5:
                            command = "MOVE_LEFT"
                        else:
                            self.ball_served = True
                            command = "SERVE_TO_LEFT"
                    else:
                        command = "NONE"
        else:                             #已經開球
        
            if (Error < margin and Error > -margin):
                command = "NONE"
            else:
                if Error > gip:
                    command = "MOVE_RIGHT"
                elif Error < -gip:
                    command = "MOVE_LEFT"
                else:                     #還沒到切球時機就等待
                    command = "NONE"
                    
        # if self.tick >=self.Timeout:
        #     self.millis = int(round(time.time() * 1000))
        #     if "blocker" in scene_info.keys():
        #         tmp = [scene_info["frame"],scene_info["status"],self.side,command,scene_info["platform_1P"][0]+20,scene_info["platform_1P"][1],scene_info["platform_2P"][0]+20,scene_info["platform_2P"][1]+30,scene_info["ball"][0]+2.5,scene_info["ball"][1]+2.5,scene_info["ball_speed"][0],scene_info["ball_speed"][1],scene_info["blocker"][0],scene_info["blocker"][1],ball[0],ball[1]]
        #         if balls!=None:
        #             for ball in balls:
        #                 tmp.append(ball[0])
        #                 tmp.append(ball[1])
                    
        #         #payload = {'frame' : scene_info["frame"] , 'status' : scene_info["status"]}
        #         payload ={}
        #         payload['frame'] = scene_info["frame"]
        #         payload['status'] = scene_info["status"]
        #         payload['side'] = self.side
        #         payload['command'] = command
        #         payload['platform_1P'] = [scene_info["platform_1P"][0]+20,scene_info["platform_1P"][1]]
        #         payload['platform_2P'] = [scene_info["platform_2P"][0]+20,scene_info["platform_2P"][1]+30]
        #         payload['ball'] = [scene_info["ball"][0]+2.5,scene_info["ball"][1]+2.5]
        #         payload['ball_speed'] = scene_info["ball_speed"]
        #         payload['blocker'] = scene_info["blocker"]
        #         payload['preball'] = ball
        #         payload['preballlog'] = balls
        #         payload['precutaddball'] = cutaddball
        #         payload['precutaddballlog'] = cutaddballs
        #         payload['precutinvball'] = cutinvball
        #         payload['precutinvballlog'] = cutinvballs
        #         payload['prebrickslog'] = prebricks
        #         payload['first'] = self.first
        #         #要發布的主題和內容
        #         if self.side =='1P':
        #             self.client.publish("Try1P/MQTT", json.dumps(payload))
        #         if self.side =='2P':
        #             self.client.publish("Try2P/MQTT", json.dumps(payload))
        #         self.data.append(tmp)
        #     else:
        #         tmp = [scene_info["frame"],scene_info["status"],self.side,command,scene_info["platform_1P"][0]+20,scene_info["platform_1P"][1],scene_info["platform_2P"][0]+20,scene_info["platform_2P"][1]+30,scene_info["ball"][0]+2.5,scene_info["ball"][1]+2.5,scene_info["ball_speed"][0],scene_info["ball_speed"][1],'None','None',ball[0],ball[1]]
        #         if balls!=None:
        #             for ball in balls:
        #                 tmp.append(ball[0])
        #                 tmp.append(ball[1])
                
        #         #payload = {'frame' : scene_info["frame"] , 'status' : scene_info["status"]}
        #         payload ={}
        #         payload['frame'] = scene_info["frame"]
        #         payload['status'] = scene_info["status"]
        #         payload['side'] = self.side
        #         payload['command'] = command
        #         payload['platform_1P'] = [scene_info["platform_1P"][0]+20,scene_info["platform_1P"][1]]
        #         payload['platform_2P'] = [scene_info["platform_2P"][0]+20,scene_info["platform_2P"][1]+30]
        #         payload['ball'] = [scene_info["ball"][0]+2.5,scene_info["ball"][1]+2.5]
        #         payload['ball_speed'] = scene_info["ball_speed"]
        #         payload['blocker'] = [None,None]
        #         payload['preball'] = ball
        #         payload['preballlog'] = balls
        #         payload['precutaddball'] = cutaddball
        #         payload['precutaddballlog'] = cutaddballs
        #         payload['precutinvball'] = cutinvball
        #         payload['precutinvballlog'] = cutinvballs
        #         payload['prebrickslog'] = prebricks
        #         payload['first'] = self.first
        #         #要發布的主題和內容
        #         if self.side =='1P':
        #             self.client.publish("Try1P/MQTT", json.dumps(payload))
        #         if self.side =='2P':
        #             self.client.publish("Try2P/MQTT", json.dumps(payload))
        #         self.data.append(tmp)
            # if (nball[1] >= L2) and (len(self.ballvel) >= 1) and(Error < margin and Error > -margin):
            #     if  self.ballvel[-1][0] >= 5:
            #         #command = "MOVE_LEFT"
            #         command = "MOVE_RIGHT"
            #     elif self.ballvel[-1][0] <= -5:
            #         #command = "MOVE_RIGHT"
            #         command = "MOVE_LEFT"
            #     else:
            #         command = "NONE"
            # else:                         #確定不會漏接就補切球
            #     if (real[1] <= L1 and real[0] >= 5):
            #         if Error > gip:
            #             command = "MOVE_RIGHT"
            #         elif Error < -gip:
            #             command = "MOVE_LEFT"
            #         else:                     #還沒到切球時機就等待
            #             command = "NONE" 
            #     else:
            #         if (Error < margin and Error > -margin):
            #             command = "NONE"
            #         else:
            #             if Error > gip:
            #                 command = "MOVE_RIGHT"
            #             elif Error < -gip:
            #                 command = "MOVE_LEFT"
            #             else:                     #還沒到切球時機就等待
            #                 command = "NONE"
                        
                
        
        #記錄球速
        if len(self.ballpos)>=1: 
            self.ballvel.append(scene_info["ball_speed"])
            
        #紀錄球的位置
        self.ballpos.append(scene_info["ball"])
        
        
        #紀錄太多就刪除
        if len(self.ballpos)>=10:
            del self.ballpos[0]
            
        if len(self.ballvel)>=10:
            del self.ballvel[0]
            
            
            
        
        return command
    
    # 子執行緒的工作函數
    def firstsearch1p(self,forms, bricks, bricksvel, prebricks):
        func_name = sys._getframe().f_code.co_name 
        testball =[20,417.5]
        testballs =[]
        testballslog =[]
        
        countlog =[]
        cblog =[]
        mcblog =[]
        
        basespeed =[]
        testspeeds =[]
     
        for i in range(0,165,5):
            testballs.append([20+i,417.5])
            testballslog.append([])
            cblog.append([])
            countlog.append([])
            mcblog.append([])
            mcblog[math.floor(i/5)].append(testballs[-1])
            
            basespeed.append(7)
            testspeeds.append((-7,-7))
        tag =-1
        first =220
        while(first==220):
            for i in range(len(testballs)):
                testballslog[i]=[]
                testballslog[i].append(testballs[i])
                testballs[i],testballslog[i],prebricks,runframe,testspeeds[i] = self.Ball_path_computer(testballs[i], testspeeds[i], forms, bricks, bricksvel, testballslog[i], prebricks,action = 'N')
                mcblog[i].append(testballs[i])
                countlog[i].append(670/basespeed[i])
                total =0
                sp = 0
                for count in countlog[i]:
                    total =total+count
                sp =round(total/100) 
                basespeed[i] =7+sp
                
                if testspeeds[i][0] >0:
                    if testspeeds[i][1] >0:
                        testspeeds[i] =(basespeed[i],basespeed[i])
                    else:
                        testspeeds[i] =(basespeed[i],-basespeed[i])
                else:
                    if testspeeds[i][1] >0:
                        testspeeds[i] =(-basespeed[i],basespeed[i])
                    else:
                        testspeeds[i] =(-basespeed[i],-basespeed[i])
                
                
                
                for testball in testballslog[i]:
                    if testball[1]<=82.5:
                        cblog[i].append(testball[0])
                
                if len(cblog[i])>1:
                    if (abs(cblog[i][-2] - cblog[i][-1])/5) > (670/basespeed[i]):
                        tag =i
                        for c in range(len(mcblog[i])-1):
                            total =0
                            sp = 0
                            for u in range(len(countlog[i])):
                                if u <=c:
                                    total =total+countlog[i][u]
                            sp =round(total/100) 
                            if (abs(mcblog[i][c][0] - mcblog[i][c+1][0])/5) > (670/(7+sp)):
                                tag =-1
                        
                # if len(cblog[i])>1:
                #     for c in range(len(cblog[i])-1):
                #         if (abs(cblog[i][c] - cblog[i][c+1])/5) > (670/basespeed[i]):
                #             tag =i
                #             break
                if tag!=-1:
                    first = tag*5+20
                    break
        self.q.put((first, func_name)) 
    def firstsearch2p(self,forms, bricks, bricksvel, prebricks):
        func_name = sys._getframe().f_code.co_name 
        testball =[20,82.5]
        testballs =[]
        testballslog =[]
        
        countlog =[]
        cblog =[]
        mcblog =[]
        
        basespeed =[]
        testspeeds =[]
        
        for i in range(0,165,5):
            testballs.append([20+i,82.5])
            testballslog.append([])
            cblog.append([])
            mcblog.append([])
            mcblog[math.floor(i/5)].append(testballs[-1])
            countlog.append([])
            
            basespeed.append(7)
            testspeeds.append((7,7))
        tag =-1
        first=220
        while(first==220):
            for i in range(len(testballs)):
                testballslog[i]=[]
                testballslog[i].append(testballs[i])
                testballs[i],testballslog[i],prebricks,runframe,testspeeds[i] = self.Ball_path_computer(testballs[i], testspeeds[i], forms, bricks, bricksvel, testballslog[i], prebricks,action = 'N')
                mcblog[i].append(testballs[i])
                countlog[i].append(670/basespeed[i])
                total =0
                sp = 0
                for count in countlog[i]:
                    total =total+count
                sp =round(total/100) 
                basespeed[i] =7+sp
                
                if testspeeds[i][0] >0:
                    if testspeeds[i][1] >0:
                        testspeeds[i] =(basespeed[i],basespeed[i])
                    else:
                        testspeeds[i] =(basespeed[i],-basespeed[i])
                else:
                    if testspeeds[i][1] >0:
                        testspeeds[i] =(-basespeed[i],basespeed[i])
                    else:
                        testspeeds[i] =(-basespeed[i],-basespeed[i])
                
                
                
                for testball in testballslog[i]:
                    if testball[1]>=417.5:
                        cblog[i].append(testball[0])
                        
                
                if len(cblog[i])>1:
                    if (abs(cblog[i][-2] - cblog[i][-1])/5) > (670/basespeed[i]):
                        tag =i
                        for c in range(len(mcblog[i])-1):
                            total =0
                            sp = 0
                            for u in range(len(countlog[i])):
                                if u <=c:
                                    total =total+countlog[i][u]
                            sp =round(total/100) 
                            if (abs(mcblog[i][c][0] - mcblog[i][c+1][0])/5) > (670/(7+sp)):
                                tag =-1
                                
                if tag!=-1:
                    first = tag*5+20
                    break
        self.q.put((first, func_name)) 
    
    def GetAllCross(self,ball,speed,forms,bricks):
        points = []
        if len(forms)>0:
            for form in forms:
                points.append( self.GetCross(form,ball,speed,'form',0))#掃描邊框的碰撞點
        # i=0
        # if bricks != None:
        #     if len(bricks)>0:
        #         for brick in bricks:
        #             if brick[0]!=None:
        #                 points.append( self.GetCross(brick,ball,speed,'bricks',i))#掃描軟磚的碰撞點
        #             i+=1
        return points
        
    def reset(self):
        """
        Reset the status
        """
        self.ball_served = False
        self.ballpos =[]
        self.ballvel =[]
        self.blocker =[]
        self.blockervel =[]
        self.data =[]
        self.first=220
        self.isfirstsearch=True
        
    def Ball_path_computer(self,ball,velocity,forms,bricks,bricksvel, balls, prebricks,action):
        # N : None, S : Super, I : Invert
        # act =['N','S','I']
        runframe =1
        speed = velocity
        while True:
            points = []
            points = self.GetAllCross(ball,speed,forms,bricks)
            
            if points ==None:
                break
            
            ball,balls,speed,frametime,srcspeed,index = self.updata_ball(points,speed,ball,balls,action)
                                        
            if ball == None or balls==None:    #例外
                ball = self.updata_fail(self.side, balls)
                break  
            
            if len(balls)>=2:
                bricks,prebricks,ball,balls,speed = self.updata_cross_bricks(bricks, bricksvel, frametime,ball, balls, srcspeed, speed, points, index, prebricks)
                                                                        
               
            #球回到板子高度就跳離
            if self.side =='1P':
                if ball[1] >=(420-5):
                    break
            if self.side =='2P':
                if ball[1] <=(50+30+5):
                    break
            #記錄迴圈次數
            runframe+=1
            if runframe >=20: # timeout
                break
        return ball,balls,prebricks,runframe,speed
    
    def updata_cross_bricks(self,bricks,bricksvel,frametime,ball,balls,srcspeed,speed,points,index,prebricks):
        #-------更新障礙物的位置依據球到碰撞點的時間-----------begin
        if len(bricks) > 0:
            if len(bricksvel) > 0:
                if bricksvel[0][0]>0:
                    newx = bricks[0][0][0]+2.5+5*frametime #障礙物往右走
                else:
                    newx = bricks[0][0][0]+2.5-5*frametime #障礙物往左走
            else:
                newx = bricks[0][0][0]+2.5+(5*frametime) #預設往右走
                
            if (newx) >= (200-20):
                newx = 2 * (200-20) - newx
            elif newx < 0:
                newx = 0 - newx
            srcbrick = (bricks[0][0][0]+2.5,bricks[0][0][1]+2.5)
            newbrick = (newx,bricks[0][0][1]+2.5)
        
        
            crossbound = self.GetBound(pos=srcbrick,size=(newx+30,20))
            cross = self.GetCross(crossbound,balls[-2],srcspeed,'bricks',0)
            #判斷是否交越障礙物
            crossframetime =None
            if cross[1] != 99999999:
                #交越點
                crosspoint = cross[0]  
                tmpballs =balls[-1]
                tmpball =ball
                balls[-1] = crosspoint
                ball = crosspoint
                
                supersrcspeed = srcspeed
                if supersrcspeed[0]>0:
                    if supersrcspeed[1]>0:
                        supersrcspeed=(supersrcspeed[0]+1,supersrcspeed[1]+1)
                    elif supersrcspeed[1]<0:
                        supersrcspeed=(supersrcspeed[0]+1,supersrcspeed[1]-1)
                elif supersrcspeed[0]<0:
                    if supersrcspeed[1]>0:
                       supersrcspeed=(supersrcspeed[0]-1,supersrcspeed[1]+1)
                    elif supersrcspeed[1]<0:
                        supersrcspeed=(supersrcspeed[0]-1,supersrcspeed[1]-1)
                
                
                
                #交越點時間
                L1 = 0
                if len(bricksvel) > 0:
                    crosspoint,crossframetime,crossinv,newTopLeftx = self.GetCrossTime(balls[-2],srcspeed,bricks[-1],bricksvel[0])
                          
                else:
                    crosspoint,crossframetime,crossinv,newTopLeftx = self.GetCrossTime(balls[-2],srcspeed,bricks[-1],(5,0))
                #crossframetime =int(abs(balls[-2][0] - crosspoint[0])/abs(srcspeed[0]))
                
                #用更快的速度更新
                if crossframetime ==None:
                    L1 = 1
                    if len(bricksvel) > 0:
                        crosspoint,crossframetime,crossinv,newTopLeftx = self.GetCrossTime(balls[-2],supersrcspeed,bricks[-1],bricksvel[0])
                    else:
                        crosspoint,crossframetime,crossinv,newTopLeftx = self.GetCrossTime(balls[-2],supersrcspeed,bricks[-1],(5,0))
                
                if crossframetime ==None or (crossframetime >= frametime):#沒發生碰撞
                    balls[-1] = tmpballs
                    ball = tmpball
                    #障礙物移動到的位置
                    if len(bricksvel) > 0:
                        if bricksvel[0][0]>0:
                            newx = bricks[0][0][0]+2.5+5*(frametime) 
                        elif bricksvel[0][0]<0:
                            newx = bricks[0][0][0]+2.5-5*(frametime) 
                        else:
                            if (bricks[0][0][0]+2.5)<=0:
                                newx = bricks[0][0][0]+2.5+5*(frametime) 
                            elif (bricks[0][0][0]+2.5)>=180:
                                newx = bricks[0][0][0]+2.5-5*(frametime) 
                            else:
                                newx = bricks[0][0][0]+2.5+5*(frametime) 
                    else:
                        if (bricks[0][0][0]+2.5)<=0:
                            newx = bricks[0][0][0]+2.5+5*(frametime) 
                        elif (bricks[0][0][0]+2.5)>=180:
                            newx = bricks[0][0][0]+2.5-5*(frametime) 
                        else:
                            newx = bricks[0][0][0]+2.5+5*(frametime) 
                else:
                    #crossframetime =round(crossframetime) #4捨6入逢五....
                    #crossframetime =math.floor(crossframetime)#捨去
                    # crossframetime =math.ceil(crossframetime)#進位
                    #判斷反射面反射速度
                    if L1 ==1:
                        if crossinv == 'invx':
                            speed = (-supersrcspeed[0],supersrcspeed[1])
                        elif crossinv == 'invy':
                            speed = (supersrcspeed[0],-supersrcspeed[1])
                        elif crossinv == 'invxy':
                            speed = (-supersrcspeed[0],-supersrcspeed[1])
                    else:
                        if crossinv == 'invx':
                            speed = (-supersrcspeed[0],supersrcspeed[1])
                        elif crossinv == 'invy':
                            speed = (supersrcspeed[0],-supersrcspeed[1])
                        elif crossinv == 'invxy':
                            speed = (-supersrcspeed[0],-supersrcspeed[1])
                        
                    
                    balls[-1] = crosspoint
                    ball = crosspoint
                    #障礙物移動到的位置
                    
                        
                    
                    newx = newTopLeftx
                    # if len(bricksvel) > 0:
                    #     #newx = bricks[0][0][0]+2.5+bricksvel[0][0]*(crossframetime) 
                    #     if bricksvel[0][0]>=0:
                    #         newx = bricks[0][0][0]+2.5+5*(crossframetime) 
                    #     elif bricksvel[0][0]<0:
                    #         newx = bricks[0][0][0]+2.5-5*(crossframetime) 
                    # else:
                    #     newx = bricks[0][0][0]+2.5+5*crossframetime #預設往右走
                
                
                
            #限制障礙物在框內並更新障礙物速度 0-180
            if newx >= (200-20):
                newx = 2 * (200-20) - newx
                if len(bricksvel) > 0:
                    bricksvel[0] = (-5,0)
            elif newx < 0:
                newx = 0 - newx
                if len(bricksvel) > 0:
                    bricksvel[0] = (5,0)
            #更新障礙物
            newbrick = (newx,bricks[0][0][1]+2.5)
            bricks[-1] = self.GetBound(pos=newbrick,size=(30,20))
            
            if crossframetime !=None:
                prebricks.append(bricks[-1][0])
            
            return bricks,prebricks,ball,balls,speed
        return [],[],ball,balls,speed
            #-------更新障礙物的位置依據球到碰撞點的時間-----------ending
        
    def updata_fail(self,side,balls):
        if balls !=None:
            if len(balls)>1:
                ball =balls[-1]
        else:
            if self.side =='1P':
                ball =(100,417.5) #沒找到碰撞點就假裝球在中線
            if self.side =='2P':
                ball =(100,82.5) #沒找到碰撞點就假裝球在中線
        return ball
    
    def updata_ball(self,points,speed,ball,balls, action):
        # N : None, S : Super, I : Invert
        act =['N','S','I']
        if len(points) > 0:
             #找出最近的碰撞點 
            lens = []
            for point in points:    
                if point[1] != 99999999:
                    lens.append(point[1])
            
            if len(lens) >0:
                srcspeed = speed
                Min = min(lens)
                index = lens.index(Min)
                #判斷反射面反射速度
                normalspeed = abs(speed[1])
                highspeed = normalspeed+3
                if speed[0]<0:
                    normalspeed =-normalspeed
                    highspeed = -highspeed
                if points[index][4] == 'invx':
                    speed = (-speed[0],speed[1])
                elif points[index][4] == 'invy':
                    if self.side =='1P':
                        if points[index][0][1] <=82.5:
                            if action == act[0]:
                                speed = (normalspeed,-speed[1])
                            elif action == act[1]:
                                speed = (highspeed,-speed[1])
                            elif action == act[2]:
                                speed = (-normalspeed,-speed[1])
                        else:
                            speed = (normalspeed,-speed[1])
                    elif self.side =='2P':
                        if points[index][0][1] >=417.5:
                            if action == act[0]:
                                speed = (normalspeed,-speed[1])
                            elif action == act[1]:
                                speed = (highspeed,-speed[1])
                            elif action == act[2]:
                                speed = (-normalspeed,-speed[1])
                        else:
                            speed = (normalspeed,-speed[1])
                elif points[index][4] == 'invxy':
                    speed = (-speed[0],-speed[1])
                
                #更新球的位置到碰撞點
                frametime = 0
                
                if points[index][0] != None:
                    
                    frametime =(abs(points[index][0][0] - ball[0])/abs(srcspeed[0]))
                    
                    #balls.append(points[index][0])
                    ball = points[index][0]
                    balls.append(ball)
                    
                    return ball,balls,speed,frametime,srcspeed,index
                
        return ball,balls,speed,0,speed,None
            
    def GetCrossTime(self,Ball,Ballvel,bound,boundvel):
        TopLeft = bound[0]
        BottomRight = bound[3]
        Time=[]
        Inv=[]
        
        xl = TopLeft[0]
        xr = BottomRight[0]
        bx0 = Ball[0]
        by0 = Ball[1]
        bdx = Ballvel[0]
        bdy = Ballvel[1]
        
        oy0 = TopLeft[1]
        if boundvel[0]>0:
            odx = 5
        elif boundvel[0]<0:
            odx = -5
        else:
            if xl <=-2.5:
                odx = 5
            elif xl >=177.5:
                odx = -5
            else:
                odx =0
        if odx ==0:
            odx =5
        
        tpmin = abs((xl - bx0)/(bdx-odx))
        tpmax = abs((xr - bx0)/(bdx-odx))
        tptag = abs((oy0-by0)/bdy)
        
        if (tpmin <= tptag) and (tptag <= tpmax):
            Time.append(tptag)
            Inv.append('invy')
            
            
        oy0 = BottomRight[1]
        
        tdmin = abs((xl - bx0)/(bdx-odx))
        tdmax = abs((xr - bx0)/(bdx-odx))
        tdtag = abs((oy0-by0)/bdy)
        
        if (tdmin <= tptag) and (tptag <= tdmax):
            Time.append(tdtag)
            Inv.append('invy')
        yu = TopLeft[1]
        yd = BottomRight[1]
        k = by0-(bdy/bdx)*bx0
        ob = TopLeft[0]
        ox0 = TopLeft[0]
        
        tlmin = abs(((yu-k)*(bdx/bdy)-ob)/odx)
        tlmax = abs(((yd-k)*(bdx/bdy)-ob)/odx)
        tltag = abs((ox0-bx0)/(bdx-odx))
        
        if (tlmin <= tltag) and (tltag <= tlmax):
            Time.append(tltag)
            Inv.append('invx')
        ob = BottomRight[0]
        ox0 = BottomRight[0]
        
        trmin = abs(((yu-k)*(bdx/bdy)-ob)/odx)
        trmax = abs(((yd-k)*(bdx/bdy)-ob)/odx)
        trtag = abs((ox0-bx0)/(bdx-odx))
        
        if (trmin <= trtag) and (trtag <= trmax):
            Time.append(trtag)
            Inv.append('invx')
        inv =None
        if len(Time) > 0:
            Min =min(Time)
            index = Time.index(Min)
            inv = Inv[index]
            point =( Ball[0] + Ballvel[0] * Min , Ball[1] + Ballvel[1] * Min)
            newTopLeftx = TopLeft[0] + 2.5 + odx *( Min)
            #修正
            if (point[1]< TopLeft[1]):
                fix = abs((point[1] - TopLeft[1])/Ballvel[1])
                point =( Ball[0] + Ballvel[0] *( Min+fix) , Ball[1] + Ballvel[1] *( Min+fix))
                newTopLeftx = TopLeft[0] + 2.5 + odx *( Min+fix)
            elif (point[1] > BottomRight[1]):
                fix = abs((point[1] - BottomRight[1])/Ballvel[1])
                point =( Ball[0] + Ballvel[0] *( Min+fix) , Ball[1] + Ballvel[1] *( Min+fix))
                newTopLeftx = TopLeft[0] + 2.5 + odx *( Min+fix)
            
            
        else:
            Min =None
            Inv =None
            point =None
            newTopLeftx =None
        
        return point,Min,inv,newTopLeftx
        
        
        
        
    def GetBound(self,pos=(0,0),size=(5,5),helf_size=(2.5,2.5),top_shift=(0,0)):
        """
        得到膨脹後的邊界
        pos       : 物體的左上角座標
        size      : 物體大小
        helf_size : 碰撞物(球本人)一半的大小，也可以是負的表示向內膨脹
        top_shift : 2p板子的碰撞高度
        """
        TopLeft     = ( pos[0] - helf_size[0],           pos[1] - helf_size[1]+top_shift[1] )
        TopRight    = ( pos[0] + size[0] + helf_size[0], pos[1] - helf_size[1]+top_shift[1] )
        BottomLeft  = ( pos[0] - helf_size[0],           pos[1] + size[1] + helf_size[1] )
        BottomRight = ( pos[0] + size[0] + helf_size[0], pos[1] + size[1] + helf_size[1] )
        bound = [ TopLeft, TopRight, BottomLeft, BottomRight ]
        return bound
    
    def GetCenter(self,pos=(0,0),size=(5,5)):
        """
        得到物體的中心點座標
        """
        center = ( pos[0] + 0.5 * size[0], pos[1] + 0.5 * size[1] ) 
        return center
    
    def GetCross(self,bound,pos,vel,name,num):
        """
        得到物體邊界與球的交點(碰撞點)
        bound : 物體的邊界
        pos   : 球的座標(中心)
        vel   : 球的速度
        name  : 物體的名稱(可能是軟磚、硬磚、邊框)
        num   : 物體的編號(索引)
        
        
        return :
            Lines[index],    碰撞邊界線上的交點座標 ( 沒撞到就給 ( None, None ) )
            Min,             球到碰撞點的最小距離 ( 沒有的話就給一個很大的值 )
            name,            物體的名稱(可能是軟磚、硬磚、邊框)
            num,             物體的編號(索引)
            inv[index]       決定球的反射方向 'invx' 反射x 
                                             'invy' 反射y
                                             'None' 無反射
        
        """
        TopLeft = bound[0]
        BottomRight = bound[3]
        
        
        #利用球座標與速度建立球的運動直線方程式 y = rate * x + b
        if vel[0]!=0:
            rate =vel[1]/vel[0] # rate
        else:
            rate =vel[1]/0.0001 # 垂直線
        b =pos[1]-rate*pos[0]
        
        inv =[]
        Lines=[]
        #L1 [TL,TR] 上邊界
        y = TopLeft[1]
        if rate==0:
            x = (( y - b ) / 0.0001)
        else:
            x = (( y - b ) / rate) #求出與上邊界的碰撞座標
        if x >= TopLeft[0] and x <= BottomRight[0]: #判斷碰撞點是否在閉區間內
            if (x-pos[0])*vel[0] >0 and (y-pos[1])*vel[1] >0:  #判斷碰撞點是否在球的前進方向
                Lines.append((x,y))
                inv.append('invy')
                
        #L2 [BL,BR] 下邊界
        y = BottomRight[1]
        if rate==0:
            x = (( y - b ) / 0.0001)
        else:
            x = (( y - b ) / rate)
        if x >= TopLeft[0] and x <= BottomRight[0]:
            if (x-pos[0])*vel[0] >0 and (y-pos[1])*vel[1] >0: 
                Lines.append((x,y))
                inv.append('invy')
                
        #L3 [TL,BL] 左邊界
        x = TopLeft[0]
        y = rate * x + b  #求出與左邊界的碰撞座標
        if y >= TopLeft[1] and y <= BottomRight[1]:
            if (x-pos[0])*vel[0] >0 and (y-pos[1])*vel[1] >0: 
                Lines.append((x,y))
                inv.append('invx')
                
        #L4 [TR,BR] 右邊界
        x = BottomRight[0]
        y = rate * x + b
        if y >= TopLeft[1] and y <= BottomRight[1]:
            if (x-pos[0])*vel[0] >0 and (y-pos[1])*vel[1] >0: 
                Lines.append((x,y))
                inv.append('invx')
        
        #沒撞到
        if len(Lines) ==0:
            return (None,None),99999999,name,num,'None'
        
        #有撞到 且碰撞點不在球的當前座標上
        lens=[]
        for line in Lines:
            Len =pow( pos[0]-line[0],2)+pow( pos[1]-line[1],2)
            if Len!=0:           
                lens.append(Len)
        #有撞到 但沒有符合條件
        if len(lens) ==0:
            return (None,None),99999999,name,num,'None'
        
        #找出離球最近的碰撞點與索引
        Min =min(lens)
        c=0
        for l in lens:    #最小的數量
            if l ==Min:
                c+=1     
        
        index = lens.index(Min)
        if c>=2:            #最小值有兩次以上表示同時碰撞XY平面
            inv[index] = 'invxy'
        
        return Lines[index],Min,name,num,inv[index]
        