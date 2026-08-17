import socket
import json
import time
from _thread import start_new_thread
import threading
import os

#csatlakozas a szervevre
def server_connect():
    global client_info
    with open("../../config.json") as file:
        server_info = json.load(file)
        file.close()
    ip = server_info["ip"]
    port = int(server_info["port"])
    server_address = (ip, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    logged_in = False
    global ingame
    ingame = False
    global pending_invite
    pending_invite = None
    global username
    global readyCheck
    readyCheck = False
    global life
    global activity_round
    activity_round = False


    #szerverrol valo uzenetek fogadasa
    try:
        while True:
            while (logged_in == False):
                username = input("Kerek egy felhasznalonevet: ")
                client_info = {
                    "type": 1,
                    "user_name": username,
                }
                json_client_info = json.dumps(client_info)
                sock.send(json_client_info.encode())

                incoming_transmission = sock.recv(1024)
                content = json.loads(incoming_transmission)
                if (content["type"] == 2):
                    print(content["message"])
                    logged_in = True
                    start_new_thread(navigation, (sock,))
                elif (content["type"] == 3):
                    print(content["message"])

            incoming_transmission = sock.recv(1024)

            content = json.loads(incoming_transmission)


            match content["type"]:

                #online jatekosok listajanak kiiratasa
                case 6:
                    onlinePlayerRecieve(sock, content)

                #invite fogadasa
                case 71:
                    inviteRecive(sock, content)

                #hibas meghivas
                case 72 | 73 | 74:
                    invite_error(content)

                #invitera valo valasz fogadasa
                case 11:
                    inviteResponse(sock, content)

                #keszen allasi alapot megadasa
                case 14:
                    ready(sock, content)

                #eletek kiosztasa
                case 16:
                    life = content["life"]
                    ingame = True

                #kor eredmenyenek fogadasa
                case 17:
                    if (content["user_name"] == username):
                        activity_round = True
                        print("A te köröd következik!")
                        round(sock)
                    else:
                        print("Az ellenfeled köre következik")
                        activity_round = False

                #kortol fuggoen aktivitas valtasa
                case 25 | 26:
                    if(activity_round):
                        if(content["type"]==25):
                            if(content["result"]==False):
                                activity_round=True
                            else:
                                life-=1
                                activity_round=False
                        else:
                            activity_round=False
                    else:
                        if(content["type"]==25):
                            if(content["result"]==True):
                                activity_round=True
                            else:
                                activity_round=False
                        else:
                            if(content["result"]==True):
                                life -= 1
                            activity_round=True

                    round(sock)

                #sebzesnel ertesites
                case 27:

                    user_name = content["user_name"]
                    elet = content["life_remaining"]
                    print(f"{user_name} életet vesztett! ({elet} élete maradt.)")

                #nyertes kihirdetese
                case 31:
                    user_name = content["user_name"]
                    if (username != user_name):
                        print("Sajnálom, vesztettél...")
                        activity_round = False

                    else:
                        print("Gratulálunk nyertél!")
                        activity_round = False

                #visszavago kerelemre valo valasz
                case 33:
                    wantsRematch(sock, content)

                #visszavago eredmenyenek ertesitese
                case 35 | 36:
                    print(content["message"])
                    if(content["type"]==35):
                        readyCheck=False
                    if (content["type"] == 36):
                        ingame = False
                        readyCheck=False

                #ranglista kiiratasa
                case 41:
                    leaderBoardRecieve(content)


                #ha az ellenfel meccs kozben  kilepne
                case 100:
                    print(content['message'])
                    print("Gratulálunk nyertél!")
                    activity_round = False
                    ingame=False

    #varatlan lecsatlakozas
    except Exception as e:
        print(e)
        print("Kliens Lecsatlakozott")

#online jatekosok kervenyezese
def onlinePlayerList(sock):
    playerList = {
        "type": 5
    }
    askForList = json.dumps(playerList)
    sock.sendall(askForList.encode())


# online jatekosok kiiratasa
def onlinePlayerRecieve(sock, content):
    online_players = content["player_list"]
    for players in online_players:
        print(f"Username: {players['user_name']}, ingame: {players['ingame']}")

#rangletra kiiratasa
def leaderBoardRecieve(content):
    leader_board = content["leader_board"]
    for players in leader_board:
        print(f"Username: {players['user_name']}, wins: {players['wins']}")

#rangletra kerese a szervertol
def leaderBoard(sock):
    leaderAsk = {
        "type": 40
    }
    askForleaderboard = json.dumps(leaderAsk)
    sock.sendall(askForleaderboard.encode())


#jatekos meghivasa
def invite(sock):
    invited_name = input("Meghivott játékos neve: ")
    inviting = {
        "type": 7,
        "invited": invited_name
    }
    inviting = json.dumps(inviting)
    sock.send(inviting.encode())

#meghivott jatekos valasza
def inviteResponse(sock, content):
    if (content["invite_status"] == True):
        print(content["invited"] + " elfogadta a meghívásod. A mérkőzés hamarosan kezdődik.")
    else:
        print(content["invited"] + " nem elfogadta a meghívásod. Meccs indítása nem történik meg.")

#hibas jatekosmeghivas
def invite_error(content):
    print(content["message"])

#meghivas fogadasa jatekostol
def inviteRecive(sock, content):
    global pending_invite
    if pending_invite is None:
        pending_invite = {}
    pending_invite["inviter"] = content["inviter"]
    print(content["inviter"] + " meghívott egy játékra! Elfogadod? (Y/N)")

#keszen allas megkerdezese
def ready(sock, content):
    global readyCheck
    readyCheck = True
    print("Készen állsz a játékra? (Y/N)")


#aktualis kor UI-ja
def round(sock):
    global  life, activity_round
    decision_json = {
        "type": 23,
        "decision": None
    }
    if(activity_round):
        print("\n\n\nA te köröd következik!")

        print(f"********************\n"
              f"Élet: " + "\033[91m/#######/\033[0m " * life + f"   ({life}/3)\n"
                                                f"********************\n"
                                                f"lehetséges döntések\n"
                                                f"-Ellenfeled lövöd (enemy)\n"
                                                f"-Magadat lövöd    (self)\n")
        time.sleep(2)
        decision = input("Döntés: ").lower()
        if (decision != "self" and decision != "enemy"):
            round(sock)
        else:
            decision_json['decision'] = decision
        decided = json.dumps(decision_json)
        sock.send(decided.encode())
    else:
        print("\n\n\nAz ellenfeled köre következik")

#visszavago megkerdezese
def wantsRematch(sock, content):
    global ingame
    wants = input("Szeretnél visszavágót? (Y/N)").lower()
    replay = {
        "type": 34,
        "replay": None
    }
    ingame = False
    if wants == "y":
        replay["replay"] = True
    else:
        replay["replay"] = False


    replayResponse = json.dumps(replay)
    sock.send(replayResponse.encode())

#lecsatlakozas
def disconnect(sock):
    disconnecting = {
        "type": 0
    }
    message_json = json.dumps(disconnecting)
    sock.send(bytes(message_json, "utf-8"))
    sock.close()
    print("Sikeresen lecsatlakozva.")
    os._exit(0)


#altalanos navigacio
def navigation(sock):
    global pending_invite
    global ingame
    global readyCheck
    global activity_round
    while True:
        time.sleep(1)
        # csak akkor megy  ha nincs jatekban
        while not ingame:
            parancs = input("Parancs: ").lower()

            #ha megvagy hivva jatekba akkor ezeket a valaszokat  nezi
            if (pending_invite is not None):
                if (parancs == "y"):
                    response = {
                        "type": 9,
                        "inviter": pending_invite["inviter"],
                        "invite_status": True
                    }
                else:
                    response = {
                        "type": 9,
                        "inviter": pending_invite["inviter"],
                        "invite_status": False
                    }
                inviteResponse = json.dumps(response)
                sock.send(inviteResponse.encode())
                pending_invite = None
                continue

            #ha keszenletet  kell figyelni akkor ez a resz  megnezi hogy ready vagy nem ready a jatekos
            if (readyCheck is True):
                response = {
                    "type": 15,
                    "ready_status": None
                }
                if (parancs == "y"):
                    response["ready_status"] = True
                    ingame = True
                else:
                    response["ready_status"] = False
                readyResponse = json.dumps(response)
                sock.send(readyResponse.encode())
                readyCheck=False
            match parancs:

                #online jatekosok kervenyezese
                case "online_players":
                    onlinePlayerList(sock)

                #rangletra kerelmezese
                case "leaderboard":
                    leaderBoard(sock)

                #jatekos meghivasa
                case "invite":
                    invite(sock)

                #lecsatlakozas
                case "disconnect":
                    disconnect(sock)
                    break


                #parancsok kiiratasa
                case "help":
                    print(f"online_players->Online playerek listaja\n"
                          f"leaderboard   ->Rangletra\n"
                          f"invite        ->Jatekos meghivasa\n"
                          f"disconnect    ->Kilepes a szerverbol\n"
                          f"help          ->Segitsegnyujtas")


#szerverre valo csatlakozas
if __name__=="__main__":
    server_connect()
