import json
import requests
import pandas as pd
import warnings
import string
import random
import time
warnings.filterwarnings("ignore")
from pathlib import Path
here = str(Path(__file__).parent.absolute())

with open(here+"//request.json",'r') as fp:
    input_req=json.load(fp)
with open(here+"//constant.json",'r') as fp:
    constant=json.load(fp)

def requesting(url,load,headers):
    """
        This requesting() makes the api call
    """
    try: 
        response= requests.post(url,json=load,headers=headers,verify=False)
        response.raise_for_status() 
        output=response.json()
        return output

    except Exception as e: 
        output={'outputs':[{'data':[{'Error':e}]}]}
        #print("HTTP Error")
        return output

def validate_jarvis(idx,response,url):
    jarvisTransactionID = response["serviceHeader"]["jarvisTransactionId"]
    time_taken = str(response["serviceHeader"]["timeTaken"])+" ms"
    ecId = response["serviceHeader"]["ecId"]

    valid = response["serviceResponse"]["rtModel"]["rtModelRes"][0]["result"]
    result = json.dumps(valid,sort_keys=True)
    try:
        if (valid["prediction"] != {}):
            # MODEL NAME
            model_name = response['serviceResponse']["rtModel"]["rtModelRes"][0]["modelName"]
            model_state = "OK"
            
        else:
            model_name = "EMPTY PREDICTION"
            model_state = "ERROR"

        return([data[idx]["model"], model_state, model_name, jarvisTransactionID, url, result[0:32759]])
    
    except: 
        model_name="MODEL DOWN"
        model_state = "ERROR"
        return([data[idx]["model"], model_state, model_name, jarvisTransactionID, url, result[0:32759]])

def validate_seldon(response,model):
    valid = response["outputs"][0]["data"][0]
    result = valid
    try:
        if(type(valid)==dict):
            model_state = "ERROR"
        else:
            valid=json.loads(valid)
            result = valid["jsonData"]["prediction"]
            if (valid["jsonData"]["prediction"] != {}):
                model_state = "OK"

        return([model, model_state, result])


    except Exception as e:
        #model_name = "NA"
        model_state = e
        return([model, model_state, result])

def seldon_validation(count,url):
    #SELDON VALIDATION
    print("STARTING SELDON VALIDATION...\ncount : ",count)
    list_seldon=[]
    timestr = time.strftime("%m-%d-%Y-%H%M%S")
        
    for idx,_input in enumerate(data):
        print("Validating "+_input["model"])
        constant['inputs'][0]['data']=_input["data"]['serviceRequest']["rtModel"]["rtModelReq"][0]["features"]
        url_seldon=url[:-27]+"v2/models/"+_input["model"]+"/infer"
        print("url=",url_seldon)
        for _count in range(count):
            model=_input['model']
            response = requesting(url_seldon,constant,headers={'content-type': 'application/json'})
            validation = validate_seldon(response,model)
            validation.append(url_seldon)
            list_seldon.append(validation)

    timestr = time.strftime("%m-%d-%Y-%H%M%S")
    print("SELDON VALIDATION COMPLETE")
    table_seldon = pd.DataFrame(list_seldon)
    table_seldon.columns=["Model","Model_state", "Result", "Endpoint"]
    table_seldon = table_seldon.loc[:,["Model", "Model_state", "Endpoint", "Result"]]
    table_seldon.to_csv(here+"//Validation//Validation_seldon-"+timestr+".csv")

    model_down=table_seldon[table_seldon['Model_state']=='ERROR']
    if(len(model_down)!=0):
        model_down.to_csv(here+"//Validation//Model_down-"+timestr+".csv")

def jarvis_validation(count,url):
    table=[]
    print("STARTING JARVIS VALIDATION...\ncount : ",count,"\nurl = ",url)
    timestr = time.strftime("%m-%d-%Y-%H%M%S")

    for idx,_input in enumerate(data):
        payload=_input["data"]
        #print(_input["model"])
        # Give the number of times you want to hit the model below inside the for loop
        for _count in range(count):
            payload['serviceHeader']['ecId'] = ''.join(random.choices(string.ascii_uppercase + string.digits, k = 10)) 
            response = requesting(url,payload,headers={'content-type': 'application/json'})
            validation = validate_jarvis(idx,response,url)
            table.append(validation)
        print(_input["model"]+" completed")
    table = pd.DataFrame(table)
    table.columns=["Model","Model_state","Model_name", "jarvisTransactionID","url", "Result"]        
    table.to_csv(here+"//Validation//Validation-"+timestr+".csv")
    print("JARVIS VALIDATION COMPLETE")
    null_prediction=table[table['Model_state']=="ERROR"]
    if(len(null_prediction)!=0):
        print("ERROR in JARVIS VALIDATION")
        null_prediction.to_csv(here+"//Validation//Null-"+timestr+".csv")
        seldon_validation(1,url)

def get_data(namespace):
    return input_req[namespace]['models']




# to get from user:
namespace = "jarvis-streams"
perform = "seldon"

if namespace == "seldon-mesh":
    url_sit = "https://jarvissit.ebiz.verizon.com/jarvis/api/getModelInsights"
    url_uat = "https://jarvisuat.ebiz.verizon.com/jarvis/api/getModelInsights"
    url_prod = "https://jarvis.verizon.com/jarvis/api/getModelInsights"

if namespace == "jarvis-streams":
    url_sit = "https://jarvissit.ebiz.verizon.com/jarvis/streams/api/getModelInsights"
    url_uat = "https://jarvisuat.ebiz.verizon.com/jarvis/streams/api/getModelInsights"
    url_prod = "https://jarvis.verizon.com/jarvis/streams/api/getModelInsights"

    #EXIT

try:
    data = get_data(namespace)
except:
    print("NAMESPACE ERROR: \nnamespace available - seldon-mesh   jarvis-streams")

try:
    if(perform=="seldon"):
        seldon_validation(5,url_prod)
    if(perform=="jarvis"):
        jarvis_validation(5,url)

except:
    print("perform should be wither 'seldon' or 'jarvis'")
# to execute
