import os
import random
import socket
from _thread import start_new_thread
import threading
import json
import time

lock = threading.Lock()


#jatekos objektum
class Connected_client:
    def __init__(self, socket, id, username):
        self.socket = socket
        self.id = id
        self.info = {}
        self.user_name = username
        self.game = None
        self.online = None
        self.ready = None
        self.replay = None
        self.life = None
        self.wins = 0

    def __str__(self):
        return f"Id: {self.id}, Felhasználónév: {self.user_name}, Játékban: {self.game} "
    def listener(self):
        global leader_board
        try:
            while True:
                # folyamatos hallgatózás a bejővő JSON állományokhoz
                incoming_transmission = self.socket.recv(1024)
                content = json.loads(incoming_transmission)
                print(content)
                match content["type"]:
                    case 5:
                        online_player_list = []
                        for c in online_clients:
                            if (c.game == None):
                                self.online = False
                            else:
                                self.online = True
                            online_player_list.append({
                                "user_name": c.user_name,
                                "ingame": self.online
                            })
                        player_list = {
                            "type": 6,
                            "player_list": online_player_list
                        }
                        playerList = json.dumps(player_list).encode()
                        self.socket.sendall(playerList)

                    # invite elküldése a megfelelő játékosnak
                    case 7:
                        invited = content["invited"]
                        for i in range(len(online_clients)):
                            client = online_clients[i]
                            if (self.user_name != invited):
                                if (client.user_name == invited):
                                    if (client.game == None):
                                        invite_player = {
                                            "type": 71,
                                            "inviter": self.user_name
                                        }
                                        invitePlayer = json.dumps(invite_player)
                                        client.socket.send(invitePlayer.encode())
                                        break
                                    else:
                                        error_message = "Az adott jatekos mar jatekban van."
                                        error_in_invite = {
                                            "type": 74,
                                            "invited": invited,
                                            "message": error_message
                                        }
                                        invite_error = json.dumps(error_in_invite)
                                        self.socket.send(invite_error.encode())
                                        break

                                elif (client.user_name != invited and i == len(online_clients) - 1):
                                    error_message = "Nem található az adott játékos, hogy meghívhasd."
                                    error_in_invite = {
                                        "type": 73,
                                        "invited": invited,
                                        "message": error_message
                                    }
                                    invite_error = json.dumps(error_in_invite)
                                    self.socket.send(invite_error.encode())
                                    break
                            else:
                                error_message = "Saját magadat nem hívhatod meg."
                                error_in_invite = {
                                    "type": 72,
                                    "invited": invited,
                                    "message": error_message
                                }
                                invite_error = json.dumps(error_in_invite)
                                self.socket.send(invite_error.encode())
                                break

                    # invite válasz fogadása a meghívott személytől
                    case 9:
                        inviter = content["inviter"]
                        status = None
                        invite_response = {
                            "type": 11,
                            "invited": self.user_name,
                            "invite_status": status
                        }
                        if content["invite_status"] == True:
                            invite_response["invite_status"] = True
                        else:
                            invite_response["invite_status"] = False

                        player1 = None

                        for i in range(len(online_clients)):
                            client = online_clients[i]
                            if client.user_name == inviter:
                                player1 = client
                                inviteReturn = json.dumps(invite_response)
                                client.socket.send(inviteReturn.encode())

                        if (content["invite_status"] == True):
                            player2 = self
                            game = Game(player1, player2)
                            player1.game = game
                            player2.game = game
                            self.game.readyCheck()

                    #jatekosok keszenallasanak ellenorzese
                    case 15:
                        if (content["ready_status"]):
                            self.ready = content["ready_status"]
                        else:
                            self.ready = content["ready_status"]
                        self.game.changeReadyStatus()

                    #aktualis kor
                    case 23:
                        if(self.game!=None):
                            self.game.round(content, self)

                    #visszavago eredmenyenek kezelese
                    case 34:
                        if (content["replay"]):
                            self.replay = content["replay"]
                        else:
                            self.replay = content["replay"]

                        if(self.game==None):
                            self.replay=None
                            continue
                        self.game.rematchDecide()

                    #rangletra elkuldese a jatekosnak
                    case 40:
                        leaderBoard_list = []
                        for i in range(len(leader_board)):
                            player = leader_board[i][0]
                            wins = leader_board[i][1]
                            leaderBoard_list.append({
                                "user_name": player,
                                "wins": wins
                            })
                        leaderBoard = {
                            "type": 41,
                            "leader_board": leaderBoard_list
                        }
                        sendLeaderBoard = json.dumps(leaderBoard).encode()
                        self.socket.sendall(sendLeaderBoard)

                # Kapcsolat bontás
                if content["type"] == 0:
                    print("lecsatlakozott-> ", self)
                    disconnect(self)
                    break
        #kapcsolatbontas
        except Exception as e:
            print(e)
            self.game.playerLeft(self)
            print(e)
            print("lecsatlakozott-> ", self)
            disconnect(self)

#jatek objektum
class Game:
    def __init__(self, player1, player2):
        self.player_list = [player1, player2]
        self.player1 = player1
        self.player2 = player2
        self.revolver = []

    #ertesiti a jatekosokat hogy keszen allnak-e
    def readyCheck(self):
        readyCheck = {
            "type": 14
        }
        ready_check = json.dumps(readyCheck)
        broadcast(ready_check, self.player_list)

    #keszenlet kezelese
    def changeReadyStatus(self):
        if (self.player2.ready == True and self.player1.ready == self.player2.ready):
            self.gameStart()
            self.player1.ready = None
            self.player2.ready = None
        else:
            if (self.player2.ready == False or self.player1.ready == False):
                self.player1.game = None
                self.player2.game = None
                self.player1.ready = None
                self.player2.ready = None

                no_ready_json = {
                    "type": 36,
                    "message": "Az egyik játékos nincs felkészülve. Visszalépés a főmenübe...."
                }
                no_match = json.dumps(no_ready_json)
                broadcast(no_match, self.player_list)
                self.player_list = []

    #jatek elinditasa
    def gameStart(self):
        game_parameters = {
            "type": 16,
            "life": 3,
        }
        self.player2.life = 3
        self.player1.life = 3

        parameters = json.dumps(game_parameters)
        broadcast(parameters, self.player_list)
        self.reload()
        self.startDecide()

    #kezdo jatekos eldontese
    def startDecide(self):
        kezdes = random.randint(0, 1)
        starting = {
            "type": 17,
            "user_name": None
        }
        if (kezdes == 0):
            starting["user_name"] = self.player1.user_name
        else:
            starting["user_name"] = self.player2.user_name

        startDecide = json.dumps(starting)
        broadcast(startDecide, self.player_list)

    #revolver ujratoltese talalatkor
    def reload(self):
        self.revolver = [0, 0, 0, 0, 0, 0]
        bullet = random.randint(0, 5)
        for i in range(len(self.revolver)):
            if i == bullet:
                self.revolver[i] = 1

    #loveskor elfordul a tar
    def magazineRotate(self):
        for i in range(len(self.revolver) - 1):
            if (i < len(self.revolver)):
                self.revolver[i] = self.revolver[i + 1]
        self.revolver[5] = 0

    #loves(true ha eles false ha vaktolteny)
    def shoot(self):
        if (self.revolver[0] == 0):
            self.magazineRotate()
            return False
        else:
            self.reload()
            return True

    #sebzeskor levonunk a jatekostol 1 eletet
    def damage(self, player):
        player.life -= 1
        damaged = {
            "type": 27,
            "user_name": player.user_name,
            "life_remaining": player.life
        }
        damaged_player = json.dumps(damaged)
        broadcast(damaged_player, self.player_list)

    #aktualis kor
    def round(self, content, player):



        if (player == self.player1):
            current_player = self.player1
            other_player = self.player2
        else:
            current_player = self.player2
            other_player = self.player1
        result = {
            "type": None,
            "result": None,
        }
        shot = self.shoot()
        match content["decision"]:
            case "self":
                result["type"] = 25
                if (shot):
                    self.damage(current_player)
                    result["result"] = True

                else:
                    result["result"] = False
            case "enemy":
                result["type"] = 26
                if (shot):
                    self.damage(other_player)
                    result["result"] = True
                else:
                    result["result"] = False

        if (current_player.life != 0 and other_player.life != 0):
            roundResult = json.dumps(result)
            broadcast(roundResult, self.player_list)
        else:
            if (self.player2.life == 0):
                winner = self.player1
            else:
                winner = self.player2
            winner_json = {
                "type": 31,
                "user_name": winner.user_name
            }

            winnerNotify = json.dumps(winner_json)
            broadcast(winnerNotify, self.player_list)
            self.roundEnd(winner)

    #egy merkozes vege
    def roundEnd(self, winner):
        global leader_board
        winner.wins += 1
        if not leader_board:
            leader_board.append([winner.user_name, 1])
        else:
            found=False
            for player in leader_board:
                if (winner.user_name == player[0]):
                    player[1] += 1
                    found=True
            if not found:
                leader_board.append([winner.user_name, 1])
        time.sleep(0.5)
        self.rematch()

    #visszavago kerdezese a jatekosoktol
    def rematch(self):
        rematch = {
            "type": 33
        }
        rematch_ask = json.dumps(rematch)
        broadcast(rematch_ask, self.player_list)

    #visszavago eldontese a valaszok alapjan
    def rematchDecide(self):
        if (self.player2.replay == True and self.player1.replay == self.player2.replay):
            self.readyCheck()
            self.player1.replay = None
            self.player2.replay = None

        else:
            if (self.player2.replay == False or self.player2.replay==False):
                self.player1.game=None
                self.player2.game=None
                no_rematch_json = {
                    "type": 35,
                    "message": "Az egyik játékos nincs felkészülve. Visszalépés a főmenübe...."
                }
                no_rematch = json.dumps(no_rematch_json)
                broadcast(no_rematch, self.player_list)
                self.player_list=[]


    #ha meccskozben kilep a jatekos
    def playerLeft(self, player):
        if(player.game==None):
            return 0
        print(player.user_name)
        if (player.user_name == self.player1.user_name):
            winner = self.player2
        else:
            winner = self.player1

        global leader_board
        winner.wins += 1
        if not leader_board:
            leader_board.append([winner.user_name, 1])
        else:
            found=False
            for player in leader_board:
                if (winner.user_name == player[0]):
                    player[1] += 1
                    found=True
                    break
            if not found:
                leader_board.append([winner.user_name, 1])
        message = f"Az ellenfeled kilépett a játékból ezért automatikusan nyertél!";
        player_left = {
            "type": 100,
            "message": message
        }
        print(winner.user_name)
        player_left_json = json.dumps(player_left).encode()
        winner.socket.send(player_left_json)

        self.player1.game = None
        self.player2.game = None

#szerver letrehozasa
def server_start():
    with open("../config.json") as file:
        server_info=json.load(file)
        file.close()
        print(server_info["ip"])
        print(server_info["port"])

    ip=server_info["ip"]
    port=int(server_info["port"])
    server_address = (ip, port)
    global sock, type, message, id
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(server_address)
    sock.listen(10)
    print(f"A Szerver elindult a kovetkezo ip cimen-> {ip}:{port}")

    start_new_thread(navigacio, ())
    global leader_board
    leader_board = []
    global online_clients
    online_clients = []
    global server_list
    server_list = []
    id = 0

    #folyamatos jatekos fogadas
    while True:
        print("Kovetkezo kliens varakozasa")
        clientsocket, address = sock.accept()
        print(f"Kliens Csatlakozott a kovetkezo cimrol-> {address}")

        start_new_thread(login, (clientsocket, id,))

        continue

#jatekos bejelentkezese
def login(clientsocket, id):
    while True:
        client_info = clientsocket.recv(1024)
        info = json.loads(client_info)
        username = info["user_name"]
        print(info)
        if (info["type"] == 1):
            if (len(online_clients) != 0):
                offline = False
                for c in online_clients:
                    if (c.user_name == username):
                        offline = False
                        message = "Hibás felhasználónév, kérlek válassz más nevet."
                        type = 3
                        continue
                    elif (c.user_name != username):
                        offline = True
                        type = 2
                        message = "Sikeres bejelentkezés!"
                if (offline == True):
                    client = Connected_client(clientsocket, id, username)
                    online_clients.append(client)
                    print(client)
                    id += 1
                    start_new_thread(client.listener, ())


            else:
                type = 2
                message = "Sikeres bejelentkezés!"
                client = Connected_client(clientsocket, id, username)
                online_clients.append(client)
                print(client)
                id += 1
                start_new_thread(client.listener, ())

        login_status = {
            "type": type,
            "message": message
        }

        loginStatus = json.dumps(login_status)
        clientsocket.send(loginStatus.encode())
        if (login_status["type"] == 2):
            break
        else:
            continue

#szerver console navigacio
def navigacio():
    global online_client
    while True:
        parancs = input()
        match parancs:

            case "exit":
                os._exit(0)

            case "uzenet":
                username = input("Username: ")
                for i in range(len(online_clients)):
                    client = online_clients[i]

                    if client.user_name == username:
                        uzenet = input("Uzenet: ")
                        client.socket.send(bytes(uzenet, "utf-8"))
                        print("Üzenet elküldve!!")
                        break
                    else:
                        print("Nem talalhato ilyen id-vel rendelkezo felhasznalo")
                        break

            case "client_list":
                for c in online_clients:
                    print(c)

            case "broadcast":
                szoveg = input("Brodast Uzenet: ")
                uzenet = "Broadcast Uzenet: " + szoveg
                broadcast(uzenet)


#jatekosok lecsatlakozasanak kezelese
def disconnect(client):
    try:
        online_clients.remove(client)
        client.socket.close()
    except Exception as e:
        print(e)

#uzenetek broadcastolasa
def broadcast(content, list):
    for felhasznalo in list:
        felhasznalo.socket.send(content.encode())

if __name__=="__main__":
    server_start()
