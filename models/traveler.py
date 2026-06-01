class Traveler:

    def __init__(self):
        self.lastFood = 0
        self.lastAccommodation = 0
        self.totalcost = 0
        self.budget = 0
        self.currentLocation = None
        self.currentTime = 0
        
    
    def getLastFood(self):
        return self.lastFood
    
    def getLastAccommodation(self):
        return self.lastAccommodation
    
    def getTotalCost(self):
        return self.totalcost
    
    def getBudget(self):
        return self.budget
    
    def getCurrentLocation(self):
        return self.currentLocation
    
    def getCurrentTime(self):
        return self.currentTime
    
    def setLastFood(self, LastFood):
        self.lastFood = LastFood
    
    
    def setLastAccommodation(self, LastAccommodation):
        self.lastAccommodation = LastAccommodation
        
    def setTotalCost(self, TotalCost):
        self.totalcost = TotalCost
        
    def setBudget(self, Budget):
        self.budget = Budget
        
    def setCurrentLocation(self, CurrentLocation):
        self.currentLocation = CurrentLocation
        
    def setCurrentTime(self, CurrentTime):  
        self.currentTime = CurrentTime
        
    #El viajero ya aterrizo
    def checkObligatory(self, nodo):
        if self.getCurrentTime() - self.getLastFood() >= 8:
            
            