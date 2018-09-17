####################################################################################################
#                                                                                                  #
#                                     MyFreeCams Plex Channel                                      #
#                                                                                                  #
####################################################################################################

from websocket  import create_connection
from datetime   import datetime
from DumbTools  import DumbKeyboard, DumbPrefs
from updater    import Updater

import urllib, json, re, time, ssl
import requests
import certifi


PREFIX          = '/video/myfreecams'
TITLE           = 'MyFreeCams'
ICON            = 'icon-default.png'
ART             = 'art-default.jpg'
OFFLINE         = 'offline.png'

BASE_URL        = 'https://www.myfreecams.com'
WEBSOCKET_URL   = 'wss://xchat20.myfreecams.com/fcsl'
SNAP_URL        = 'https://snap.mfcimg.com/snapimg/{server}/320x240/mfc_{room}?no-cache={unique}'
DATA_URL        = BASE_URL + '/php/FcwExtResp.php?respkey={respkey}&type={type}&opts={opts}&serv={serv}'
EXPLORER_URL    = BASE_URL + '/php/model_explorer.php?get_contents=1&selected_field={field}&sort={sort}&selection={selection}&search={search}&mode={mode}&page={page}&night_mode=0&{unique}'

####################################################################################################

def Start():
    ObjectContainer.title1      = TITLE
    ObjectContainer.art         = R(ART)

    DirectoryObject.thumb       = R(ICON)
    DirectoryObject.art         = R(ART)

    InputDirectoryObject.art    = R(ART)

    VideoClipObject.art         = R(ART)

    HTTP.CacheTime              = 0

####################################################################################################

def GetModelData():
    session_re = re.compile(r'''\04522opts\04522\:(?P<opts>\d+),\04522respkey\04522\:(?P<respkey>\d+),\04522serv\04522\:(?P<serv>\d+),\04522type\04522\:(?P<type>\d+)''')

    send_msg_hello  = "hello fcserver\n\0"
    send_msg_login  = "1 0 0 20071025 0 guest:guest\n\0"
    send_msg_ping   = "0 0 0 0 0\n\0"
    send_msg_logout = "99 0 0 0 0"    

    ws = create_connection(WEBSOCKET_URL, sslopt={"cert_reqs": ssl.CERT_NONE})

    ws.send(send_msg_hello)
    ws.send(send_msg_login)

    loop_number     = 0
    status_regex    = False

    while status_regex is not True:
        if loop_number is 20:
            Log.Debug("Websocket loop terminated after 20 attempts")
            return

        ws.send(send_msg_ping)
        data_ws = ws.recv()

        try:
            mfc_session     = session_re.search(data_ws)
            data_opts       = mfc_session.group("opts")
            data_respkey    = mfc_session.group("respkey")
            data_serv       = mfc_session.group("serv")
            data_type       = mfc_session.group("type")

            if mfc_session is not None:
                status_regex = True
        except:
            loop_number += 1
            Log.Debug("-- RESEND WEBSOCKET DATA -- {0} --".format(loop_number))

    ws.send(send_msg_logout)
    ws.close()    

    if status_regex == True:
        cookies     = {"cid": "3149", "gw": "1"}
        response    = requests.get(DATA_URL.format(
                            opts    = data_opts,
                            respkey = data_respkey,
                            serv    = data_serv,
                            type    = data_type
                        ), cookies=cookies)

        Log.Debug('RESPONSE: {}'.format(response))    

    return response

####################################################################################################

@handler(PREFIX, TITLE, thumb=ICON, art=ART)
def MainMenu():
    oc = ObjectContainer(title2=TITLE, art=R(ART), no_cache=True)

    Updater(PREFIX + '/updater', oc)
    
    oc.add(DirectoryObject(
        key     = Callback(CamList, title='All Cams', page=1), 
        title   = 'All Cams'
    ))

    return oc

####################################################################################################

@route(PREFIX + '/cams/{page}', page=int)
def CamList(title, page=1):
    oc          = ObjectContainer(title2=title, art=R(ART), no_cache=True)

    modelData   = GetModelData()

    request     = EXPLORER_URL.format(
        field       = 'room_topic',
        sort        = 'cam_score',
        selection   = 'all',
        search      = '',
        mode        = '',
        page        = page,
        unique      = time.time()
    )

    response    = requests.get(request, verify=False)
    contents    = response.text.splitlines()

    """
    response    = urllib.urlopen(request, context=context)
    contents    = str(response.read()).splitlines()
    """

    for line in contents:
        if 'aList[' in line:
            block           = line.split('] = " ')[-1]
            block           = block.strip()[:-1]
            block           = block.replace('i"+"mg','img')
            html            = HTML.ElementFromString(block)

            camName         = html.xpath('//b/span/text()')[0]

            re_uid          = r"\d+"
            re_username     = camName
            data_channel_re = re.compile(r'''
                \133(?:\s+)?(["'](?P<username>{0})["']\,?\d+,(?P<uid>{1})[^\135]+)\135
                '''.format(re_username, re_uid), re.VERBOSE | re.IGNORECASE)

            try:
                data_channel = data_channel_re.search(modelData.text)
                data_channel = data_channel.group(0)
                data_channel = json.loads(data_channel)
                Log.Debug("FOUND [{}] IN DATASET".format(camName))
            except:
                Log.Debug("DID NOT FIND [{}] IN DATASET, SKIPPING".format(camName))
                continue

            camBlurb    = ''
            camTopic    = ''
            camSummary  = ''
            
            modelID     = int(data_channel[2])
            camStatus   = int(data_channel[3])
            camServer   = int(data_channel[6])

            if camStatus is 0:
                camBlurb    = data_channel[15]
                camTopic    = urllib.unquote(data_channel[23]).decode('utf8')

                camUrl      = BASE_URL + '/?i={}&n={}&s={}'.format(modelID, camName, camServer)
                camPreview  = SNAP_URL.format(
                                    server  = camServer - 500, 
                                    room    = modelID + 100000000, 
                                    unique  = time.time()
                                )
            else:
                camUrl      = BASE_URL + '/#{}'.format(camName)
                camPreview  = R(OFFLINE)

            if len(camBlurb) > 0:
                camSummary += '\n\n' if len(camSummary) > 0 else ''
                camSummary += camBlurb

            if len(camTopic) > 0:
                camSummary += '\n\n' if len(camSummary) > 0 else ''
                camSummary += camTopic

            oc.add(VideoClipObject(
                url     = camUrl,
                title   = camName,
                thumb   = camPreview,
                year    = datetime.now().year,
                summary = camSummary if len(camSummary) > 0 else 'No summary',
                tagline = camBlurb
            ))

    if len(oc) > 0:
        oc.add(NextPageObject(
            key     = Callback(CamList, title=title, page=page+1),
            title   = 'Next Page'
        ))

        return oc

    return MessageContainer(header='Warning', message='Page Empty')

####################################################################################################
