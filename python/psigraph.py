#python graphing module that I had to write,
#because pyplot does not import for me no matter what I do.

import tkinter as tk

class barGraph:
    def __init__(self,c,barsN):
        #c must be a canvas object, or you will be sad.
        #barsN is the number of bars in your graph
        #graphics are preceded with g_
        self.c=c
        self.barsN=barsN #number of bars
    def define(self,x1,y1,x2,y2,yvals):
        #this precalculates values and is called from the prep function.
        #you can also call it here.
        #yvals must be an array.
        self.xvals=[0]*self.barsN
        self.x1=x1
        self.x2=x2
        self.y1=y1
        self.y2=y2
        self.ylow=yvals[0]
        self.yhigh=yvals[-1]
        #print(self.yhigh)
        self.yvals=yvals
        self.xinc=(x2-x1)/self.barsN
        self.yinc=(y2-y1)/(self.yhigh-self.ylow)
        self.yunits=""
        self.xlabels=range(0,self.barsN)
    def set_yunits(self,yunits):
        self.yunits=yunits
        for i in range(0,len(self.yvals)):
            self.c.itemconfig(self.g_yvals[i],text=str(self.yvals[i])+self.yunits)
    def set_xlabels(self,xlabels):
        self.xlabels=xlabels
        for i in range(0,self.barsN):
            self.c.itemconfig(self.g_xlabels[i],text=self.xlabels[i])
    def set_xcolors(self,xcolors):
        self.xcolors=xcolors
        for i in range(0,self.barsN):
            self.c.itemconfig(self.g_bars[i],fill=self.xcolors[i])
    def set_values(self,v):
        #make sure v is bars elements long.
        self.xvals=v
        for i in range(0,self.barsN):
            self.c.coords(self.g_bars[i],self.x1+self.xinc*i+self.xinc*0.1,self.y2-self.yinc*(self.xvals[i]),self.x1+self.xinc*i+self.xinc*0.9,self.y2)
    def prep(self,x1,y1,x2,y2,yvals):
        #call this only once. It set up graphics.
        #ylow and yhigh are the extents of the y axis.
        #x1y1x2y2 are extents.
        #call this only once.
        self.define(x1,y1,x2,y2,yvals)
        self.g_backdrop=self.c.create_rectangle(x1,y1,x2,y2,fill="white")
        self.g_axisy=self.c.create_line(x1,y1,x1,y2,fill="black")
        self.g_axisx=self.c.create_line(x1,y2,x2,y2,fill="black")
        self.g_yvals=[]
        self.g_ymarks=[]
        for i in range(len(self.yvals)):
            self.g_yvals.append(self.c.create_text(x1-20,y2-(y2-y1)/(len(self.yvals)-1)*i,justify=tk.RIGHT,text=str(self.yvals[i])+self.yunits))
        if len(self.yvals)>2:
            for i in range(1,len(self.yvals)-1):
                self.g_ymarks.append(self.c.create_line(x1,y2-(y2-y1)/(len(self.yvals)-1)*i,x2,y2-(y2-y1)/(len(self.yvals)-1)*i,fill="grey"))
        self.g_bars=[]
        self.g_xlabels=[]
        for i in range(0,self.barsN):
            self.g_bars.append(self.c.create_rectangle(x1+self.xinc*i+self.xinc*0.1,self.y2-self.yinc*(self.xvals[i]),x1+self.xinc*i+self.xinc*0.9,y2,fill="red"))
            self.g_xlabels.append(self.c.create_text(x1+self.xinc*i+self.xinc*0.5,y2+20,text=self.xlabels[i]))
        self.set_xcolors(["red"]*self.barsN)


