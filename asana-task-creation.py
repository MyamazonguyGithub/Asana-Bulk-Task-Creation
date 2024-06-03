import time
import requests
from functools import wraps
import json
import os
from dotenv import load_dotenv
import datetime
import re
import validators

load_dotenv('C:\\Users\\Ozild\\AppData\\Local\\Packages\\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\\Code\\asana-task-duplication\\asana-task-duplication.env')

hubspot_api_key = os.getenv('HUBSPOT_API_KEY')
asana_access_token = os.getenv('ASANA_ACCESS_TOKEN')

asana_headers = {
    "Authorization": "Bearer " + asana_access_token,
    "Content-Type": "application/json"
}

hubspot_headers = {
    "Authorization": "Bearer " + hubspot_api_key,
    "Content-Type": "application/json"
}
#Exponential Back Off Rate Limit Error Handling
def retry(attempts=5, delay=1, backoff=2):
    def retry_decorator(func):
        @wraps(func)
        def func_with_retry(*args, **kwargs):
            local_attempts, local_delay = attempts, delay
            while local_attempts > 1:
                try:
                    result = func(*args, **kwargs)
                    if isinstance(result, requests.Response):
                        result.raise_for_status()
                    return result
                except requests.exceptions.HTTPError as e:
                    print(f"Request failed, retrying in {local_delay} seconds...")
                    time.sleep(local_delay)
                    local_attempts -= 1
                    local_delay *= backoff
            return func(*args, **kwargs)
        return func_with_retry
    return retry_decorator

def validate_url(url):
    if not validators.url(url):
        return False
    return True

# Gets HubSpot Properties
@retry(attempts=5, delay=2, backoff=2)
def get_current_clients():
    offset = 0
    url = "https://api.hubapi.com/crm/v3/objects/companies/search"
    clients = []
    while True:
        body = json.dumps({
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "lifecyclestage",
                            "operator": "IN",
                            "values": ["45633643","45777159"]
                        },
                        {
                            "propertyName": "client_status",
                            "operator": "EQ",
                            "value": "Active"
                        }
                    ]
                }
            ],
            "properties": ["asana_project", "name","govisually_link","amazon_seller_link","secondary_user_email","google_folder","website","design_brief"],
            "limit": 100,
            "after": offset
        })

        response = requests.post(url, headers=hubspot_headers, data=body)
        response_json = response.json()
        properties_to_check = ["govisually_link", "amazon_seller_link", "google_folder", "website", "design_brief","secondary_user_email"]
                        
        for client in response_json['results']:
            client_properties = client['properties'].copy()
            for prop in properties_to_check:
                if prop in client_properties:
                    if client_properties[prop]:
                        # Check if "<" or " " is part of a URL or if the value is "N/A" or "n/a"
                        if "<" in client_properties[prop] or " " in client_properties[prop] or re.sub(r'\W+', '', client_properties[prop]).lower() == "na":
                            client_properties[prop] = f'https://app.hubspot.com/contacts/21417700/record/0-2/{client["id"]}'
                        # Add protocol if not present
                        elif not client_properties[prop].startswith(('http://', 'https://')):
                            client_properties[prop] = 'http://' + client_properties[prop]
                    else:
                        client_properties[prop] = f'https://app.hubspot.com/contacts/21417700/record/0-2/{client["id"]}'
                else:
                    client_properties[prop] = f'https://app.hubspot.com/contacts/21417700/record/0-2/{client["id"]}'
            if 'name' in client_properties and client_properties['name'] and ' -' in client_properties['name']:
                client_properties['name'] = client_properties['name'].split(' -')[0]
            client['properties'] = client_properties
        
        clients.extend(response_json['results'])
        if response_json.get('paging'):
            offset = response_json['paging']['next']['after']
        else:
            return clients
# This function is used to retrieve the details of a specific project from Asana.
# It takes a project's GID (Globally Unique Identifier) as an argument and makes a GET request to Asana's API.
# The function returns the 'data' field from the response, which contains the project details.
# This function is used to check if a task already exists in the project or to add a new task to the project.
#
@retry(attempts=5, delay=2, backoff=2)
def get_project(project_gid):
    url = f"https://app.asana.com/api/1.0/projects/{project_gid}"
    response = requests.get(url, headers=asana_headers)
    resp_json = response.json()
    return resp_json['data']

#
# This function checks if a task with a specific name exists in a given project on Asana.
# It takes a project's GID and the task name as arguments and makes a GET request to Asana's API.
# The function iterates over the tasks in the project (up to a limit of 100 tasks per request due to API limitations).
# If a task with the given name is found, the function returns True.
# If no task with the given name is found after checking all tasks, the function returns False.
#
@retry(attempts=5, delay=2, backoff=2)
def check_task_exists(project, name):
    url = f"https://app.asana.com/api/1.0/projects/{project}/tasks"
    params = {
        "opt_fields": "name,completed",
        "limit": 100,
        "completed_since": "now"  # only fetch tasks that are incomplete
    }
    response = requests.get(url, headers=asana_headers, params=params)
    resp_json = response.json()
    if 'errors' in resp_json:
        print(f"Error checking task existence: {resp_json['errors']}")
        return False
    elif 'data' in resp_json:
        for task in resp_json['data']:
            if task['name'] == name and not task['completed']:
                return True
        if 'paging' in resp_json and 'next_page' in resp_json['paging']:
            return check_task_exists(project, name, resp_json['paging']['next_page'])
        return False
    else:
        print(f"Unexpected response: {resp_json}")
        return False
#
# This function creates a new task in Asana with a given name and properties.
# It takes the task name and a dictionary of properties as arguments and makes a POST request to Asana's API.
# The function returns the 'data' field from the API response, which contains the details of the created task.
#
@retry(attempts=5, delay=2, backoff=2)
def create_task(name, properties):
    url = "https://app.asana.com/api/1.0/tasks"

    for key in ['govisually_link', 'amazon_seller_link', 'secondary_user_email', 'google_folder', 'website', 'design_brief']:
        if key not in properties or not properties[key]:
            print(f"Error: Missing or empty property: {key}")
            return None
        if key != 'secondary_user_email' and not validators.url(properties[key]):
            print(f"Error: Invalid URL format for property: {key}")
            return None

    description = f"""<body><h1>Section 1:</h1><h2>Request:</h2><ul><li><strong># of Images:</strong> [Enter the number of images required]</li>
        <li><strong>Approved Template:</strong> [Insert Link To Reference Task or Listing]</li>
        <li><strong>GoVisually Project Link:</strong> <a href="{properties.get('govisually_link', '')}">{properties.get('govisually_link', '')}</a></li>
        <li><strong>ASIN's:</strong></li>
        <ul><li>[Insert ASIN(s)]</li></ul></ul> <hr><h1>Section 2: Links and Resources</h1><ul>
        <li><strong>Seller Central Link:</strong> <a href="{properties.get('amazon_seller_link', '')}">{properties.get('amazon_seller_link', '')}</a></li>
        <li><strong>SC Email Address:</strong> <a href="mailto:{properties.get('secondary_user_email', '')}">{properties.get('secondary_user_email', '')}</a></li>
        <li><strong>Client Folder:</strong> <a href="{properties.get('google_folder', '')}">{properties.get('google_folder', '')}</a></li>
        <li><strong>Google Drive Assets Folder:</strong> [Insert Google Drive Link]</li>
        <li><strong>Website Link:</strong> <a href="{properties.get('website', '')}">{properties.get('website', '')}</a></li>
        <li><strong>Design Brief Link:</strong> <a href="{properties.get('design_brief', '')}">{properties.get('design_brief', '')}</a></li>
        <li><strong>GoVisually Client Board:</strong> <a href="{properties.get('govisually_link', '')}">{properties.get('govisually_link', '')}</a></li></ul> <hr><h1>Section 3: Project Details</h1><ul><li><strong>MKL:</strong> [Insert MKL Link]</li>
        <li><strong>Main Image Callout/Ingredient:</strong> [Describe the main image callout or key ingredient]</li>
        <li><strong>Demographic/Avatar:</strong> [Describe the target demographic or customer avatar]</li>
        <li><strong>Competitor Link:</strong> [Insert competitor's link for reference]</li>
        <li><strong>Unique Selling Propositions:</strong></li>
        <li><strong>Client Direction:</strong> [Insert any information that the client has given pertaining to execution of design tasks]</li>
    </ul>
    </body>"""
    data = {
        "data": {
            "name": f"{name.split(' -')[0]} - Image/Design Task Type - ASIN - Product Name",
            "html_notes": description,
            "due_on": datetime.date.today().isoformat(),
            "workspace": "1137917655103002"  # Add workspace ID here
        }
    }
    response = requests.post(url, headers=asana_headers, data=json.dumps(data))
    resp_json = response.json()
    if 'errors' in resp_json:
         print(f"Error creating task: {resp_json['errors']}")
         return None
    elif 'data' in resp_json:
        return resp_json['data']
    else:
        print(f"Unexpected response: {resp_json}")
        return None

#
# This function adds the task to a specific project in Asana.
# It takes a task's GID and a project's GID as arguments and makes a POST request to Asana's API.
# The function sends a JSON payload with the project's GID in the 'data' field.
# The API response is printed to the console.
# If the request is successful, the task is added to the project and the API response includes the details of the updated task.
#
@retry(attempts=5, delay=2, backoff=2)
def add_project(task, project):
    url = f"https://app.asana.com/api/1.0/tasks/{task}/addProject"
    data = json.dumps({
        "data": {
            "project": project
        }
    })
    response = requests.post(url, headers=asana_headers, data=data)
    resp_json = response.json()
    print(resp_json)


#
# This is the main function that orchestrates the creation of tasks in Asana for a list of clients.
# It first retrieves the current clients using the 'get_current_clients' function.
# It then iterates over each client and checks if a task already exists for the client's project in Asana.
# If a task exists, the function prints a message and does not create a new task.
# If a task does not exist, the function creates a new task using the 'create_task' function and adds it to the client's project using the 'add_project' function.
# The function keeps track of the projects for which a task has been created using a set named 'created_projects'.
# After a task is created for a project, the function prints a message and continues to the next project.
# The function is called at the end to start the task creation process.
#
@retry(attempts=5, delay=2, backoff=2)
def main():
    use_gid_list = False  # Change this to True to process specific GIDs
    # List of GIDs to process
    process_gids = ['1206943948754457'] if use_gid_list else [client['properties']['asana_project'].split("/")[-2] for client in get_current_clients() if client['properties']['asana_project']]

    clients = get_current_clients()
    processed_clients = set()  # keep track of processed clients
    created_projects = set()  # keep track of projects for which a task has been created
    errored_projects = set()  # keep track of projects for which task creation failed
    skipped_projects = set()  # keep track of projects for which task creation was skipped

    for gid in process_gids:

        client = next((client for client in clients if client['properties']['asana_project'] and client['properties']['asana_project'].split("/")[-2] == gid), None)
        if client is None:
            continue

        client_gid = client['properties']['asana_project'].split("/")[-2]
        if client_gid in processed_clients:
            continue

        processed_clients.add(client_gid)  # mark this client as processed

        task_name = f"{client['properties']['name'].split(' -')[0]} - Image/Design Task Type - ASIN - Product Name"
        task_exists = check_task_exists(gid, task_name)
        if task_exists:
            print(f"Task already exists for client {client['properties']['name']}. Skipping...")
            skipped_projects.add(gid)
            continue

        try:
            client_task = create_task(client['properties']['name'], client['properties'])
            if client_task is None or 'gid' not in client_task:
                print(f"Failed to create task for client {client['properties']['name']}. Skipping...")
                errored_projects.add(gid)
                continue
            client_task_gid = client_task['gid']
            add_project(client_task_gid, gid)
            created_projects.add(gid)  # mark this project as having a task created
            print(f"Created task for project with GID: {gid}")
        except Exception as e:
            print(f"Error creating task: {e}. Moving to the next one.")
            errored_projects.add(gid)  # mark this project as having an error
            continue  # skip to the next iteration of the loop if an error occurs

    # return the sets of created, errored, and skipped projects
    return created_projects, errored_projects, skipped_projects

created_projects, errored_projects, skipped_projects = main()
print(f"Created Total: {len(created_projects)} | GIDs: {created_projects}.")
print(f"Errored Total: {len(errored_projects)} | GIDs: {errored_projects}.")
print(f"Skipped Total: {len(skipped_projects)}")
total = len(created_projects) + len(errored_projects) + len(skipped_projects)
print(f"Combined Total: {total}")