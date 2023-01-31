from flask import Flask
from flask import render_template
from flask import redirect
from flask import request
from flask import session
from Board_Elements import *
from Powerup import Powerup
from Player import Player
import random
import uuid



app = Flask(__name__)
app.secret_key = '1221'

games = {}
def check():
    if 'key' not in session or 'games' not in globals():
        return True
    return False
class Game:
    def __init__(self, blue, red):
        #Setting players
        self.players = list()
        self.players.append(Player(red))
        self.players.append(Player(blue))
        #Setting board + pawns
        self.board = Board(self.players)
        self.selected = None
        #Setting powerups
        self.powerups = Powerup(self)
        #Linking powerups with pawns
        for position_x in range(10):
            self.board.gameboard[0][position_x][1].set_powerups(self.powerups)
            self.board.gameboard[1][position_x][1].set_powerups(self.powerups)
            self.board.gameboard[6][position_x][1].set_powerups(self.powerups)
            self.board.gameboard[7][position_x][1].set_powerups(self.powerups)
        # Randomizing who is starting
        if random.randint(0,1) : random.shuffle(self.players)
        self.turn = self.next_turn()
        self.current = next(self.turn)

    def select(self, pos):
        self.selected=(pos[0],pos[1])
        return self.board.move_check(pos)
    def deselect(self):
        self.selected=None
    def move(self, pos):
        self.board.move_action(self.selected, pos)
        self.deselect()
        self.current = next(self.turn)
    def activate_power(self, power):
        #1. Activates power - function(type) 2.If activation is successful removes power from inventory
        if self.powerups.powerup_dict[power][0](self.powerups.powerup_dict[power][1]) :
            self.board.gameboard[self.selected[0]][self.selected[1]][1].remove_powerup(power)

    def next_turn(self):
        #Switches player's turn & generates powerups
        powergen=0 #Note that due to self.current in init, this will always be powergen+1 at start
        turn = lambda : random.randint(3, 6)
        generation_turn = turn()
        while True :
            #if this is the last player in the player-list it will start over
            for player in self.players :
                powergen += 1
                if powergen == generation_turn:
                    powergen = 0
                    generation_turn = turn()
                    self.generate()
                yield player
    def generate(self):
        #Generates powerups on the board
        #Generate random amount of powerups (1-4)
        for x in range(1,random.randint(1,4)) :
          self.board.power_place( random.choice(list(self.powerups.powerup_dict.keys())) )


class Board:
    def __init__(self, players):
        ''' player table'''
        #Generates 8 x 10 array. !!Coordinates are (y,x) (rows,columns)!!
        #The information about contents of a tile in the gameboard are located in gameboard[y][x][0/1/2]
        #Where indexes: 0-Tile obj 1- Pawn obj  2- powerup string (dictionary key)
        self.gameboard = [[ [Tile(),None,None] for i in range(10) ]for j in range(8)]
        #Populates game board with Pawns
        for position_x in range(10):
            self.gameboard[0][position_x].insert(1,Pawn(players[0]))
            self.gameboard[1][position_x].insert(1,Pawn(players[0]))
            self.gameboard[6][position_x].insert(1,Pawn(players[1]))
            self.gameboard[7][position_x].insert(1,Pawn(players[1]))

    def move_check(self, pos):
        '''Checks if a Pawn on a given position can move. RETURNS all the positions to where it can move'''
        # The way this works: 1.Creates a table with all possible move positions
        # 2. For each possible move position if it is accessible. If not then it removes this position from table
        y = pos[0]
        x = pos[1]
        # DOWN UP RIGHT LEFT
        move = [(y+1, x), (y-1,x), (y, x+1), (y, x-1)]

        if 'move_diagonal' in self.gameboard[y][x][1].attributes :
        ##    #LOWER-RIGHT LOWER-LEFT UPPER-RIGHT UPPER-LEFT
            move.extend([(y+1,x+1), (y+1,x-1), (y-1,x+1), (y-1,x-1)])
        move_av = move.copy()
        for position in move_av:
        #Prepping the values
            y = position[0]
            x = position[1]

        #Tile existence/board existence
            if y > 7 or y < 0 or x > 9 or x < 0 : move.remove(position)
        #Tile height difference - Tile height -1 > Pawn tile height AND Pawn has no jetpack
        #-1 enables you to go up
            elif self.gameboard[y][x][0].height -1 > self.gameboard[pos[0]][pos[1]][0].height and 'climb-tile' not in self.gameboard[pos[0]][pos[1]][1].attributes: move.remove(position)
        #Tile state
            elif self.gameboard[y][x][0].state == 'destroyed' : move.remove(position)
        #If pawn exists on location >> Pawn == friend or (if not friend then enemy) enemy is jump proof
            elif self.gameboard[y][x][1] :
                if self.gameboard[pos[0]][pos[1]][1].owner == self.gameboard[y][x][1].owner or 'jump-proof' in self.gameboard[y][x][1].attributes : move.remove(position)
        #Teleporters --WIP
        return tuple(move)
    def move_action(self, sel, to):
        position_from = self.gameboard[sel[0]][sel[1]]
        position_to = self.gameboard[to[0]][to[1]]
        #If a powerup then pick it up
        if position_to[2] : self.power_pickup(sel,to)
        #Move Pawn (if an enemy pawn is on position_to it automatically deletes it)
        position_to[1] = position_from[1]
        position_from[1] = None
    def power_pickup(self, pawn, powerup):
        self.gameboard[pawn[0]][pawn[1]][1].collect_powerup(self.gameboard[powerup[0]][powerup[1]][2])
        self.gameboard[powerup[0]][powerup[1]][2]=None
    def power_place(self,powerup):
        limit = 100 #This is not an elegant solution, will fix later.
        while limit:
            loc=self.gameboard[random.randint(0,7)][random.randint(0,9)]
            limit -= 1
            # won't place powerup if the tile is destroyed there is a pawn or powerup on tile
            if loc[0].state != 'destroyed' and not loc[1] and not loc[2]:
                loc[2] = powerup
                break


@app.route('/')
def index():
    if 'key' not in session:
        session['key'] = uuid.uuid4()
    return render_template('index.html')

@app.route('/hotseat',  methods=['POST','GET'])
def hotseat_setup():
    if check() : return redirect('/')
    if request.method == 'POST':
        games[session['key']] = Game(request.form.get('blue'), request.form.get('red'))
        return redirect('/game')
    else:
        return render_template('hotseat_setup.html')

@app.route('/game', methods=['GET','POST'])
def game():
    if check() or session['key'] not in games  : return redirect('/')
    #Conversion to shorter variable names
    game = games[session['key']]
    action = request.form.get('action')
    pos=[request.form.get('y', type=int ),request.form.get('x', type=int)]  #Note. position will always be (y,x)

    # game.victory_check() : redirect('/game/winner')
    if action == 'select' :
        #Prevents form going to previous page and selecting piece
        if pos and game.board.gameboard[pos[0]][pos[1]][1].owner == game.current:
            return render_template('game.html', game=game, turn=game.current, movement=game.select(pos), selected=game.board.gameboard[pos[0]][pos[1]][1])
    if game.selected: #if pawn is selected it allows for other actions
        if action == 'move' : game.move(pos) #next turn | deselects pawn
        elif action == 'powerup' : game.activate_power(request.form.get('powerup'))
        elif action == 'deselect' : game.deselect()
    return render_template('game.html', game=game, turn=game.current)

if __name__ == '__main__':
    app.run(host="wierzba.wzks.uj.edu.pl", port=5105, debug=True)
