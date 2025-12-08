from tkinter import *
from tkinter import ttk
from tkinter import messagebox
###
gui = Tk()
gui.title('HackWarrior')
gui.geometry('600x600')
l1 = Label(gui,text='HackWarrior System',font=('Tahoma',20) ,fg='Navy')
l1.place(x=30,y=20)
###
b1 = ttk.Button(gui,text='Test')
b1.pack(ipadx=30,ipady=10)
###
def Button2() :
    text = 'xxxxxxxxxxxxxxxxxxxxxxxxx'
    messagebox.showinfo('Information',text)
###    
fb1 = Frame(gui)
fb1.place(x=50,y=200)
b2 = ttk.Button(fb1,text='Test',command=Button2)
b2.pack(ipadx=30,ipady=10)

###
gui.mainloop()

