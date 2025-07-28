class Hero:
    def __init__(self):
        self.position = '00'

    def move(self, direction):
        match direction:
            case 'up':
                if self.position[0] == '0':
                    raise Exception("Can't move Up!")
                
                self.position = str(int(self.position[0])-1)+self.position[1]

            case 'down':
                if self.position[0] == '4':
                    raise Exception("Can't move Down!")
                
                self.position = str(int(self.position[0])+1)+self.position[1]
            case 'left':
                if self.position[1] == '0':
                    raise Exception("Can't move left!")
                
                self.position = self.position[0]+str(int(self.position[1])-1)
            case 'right':
                if self.position[1] == '4':
                    raise Exception("Can't move right!")
                
                self.position = self.position[0]+str(int(self.position[1])+1)
            

h = Hero()
try:
    h.move('right')
    print(h.position)  # Should print '00'     # Should raise an exception
except Exception as e:
    print(e)  # Output the exception message