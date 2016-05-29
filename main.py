import json
import time

import gitlab
import requests
import requests.auth


host = input("Gitlab Host (https://gitlab.com/): ")
if host == '':
    host = 'https://gitlab.com/'
token = input("Private Token: ")
gl = gitlab.Gitlab(host, token=token)
gl_api = host + "api/v3/"
print("Parsing Projects...")
projects = gl.getprojects()
for i, project in enumerate(projects):
    print(str(i)+": "+project['path_with_namespace'])
project = projects[int(input("Select project: "))]
project_id = str(project['id'])
print("Parsing Issues...")
headers = {"PRIVATE-TOKEN": token}
issues = requests.get(gl_api + "projects/" + project_id + '/issues?per_page=100', headers=headers).json()
issues.reverse()  # sort parameter doesn't work, so we need to reverse issues manually

print("Parsing labels...")
labels = requests.get(gl_api + "projects/" + project_id + "/labels", headers=headers).json()

print("Parsing comments...")
for i, issue in enumerate(issues):
    print(str(i+1)+": "+issue['title']+"( ID "+str(issue['id'])+" )")
    #try:
    resp = requests.get(gl_api + "projects/" + project_id + "/issues/" +
                str(issue['id']) +"/notes", headers=headers).json()
    resp.reverse()  # Again, sort does not work
    issue['comments'] = resp
    #except:
    #    issue['comments'] = []

github_api = "https://api.github.com/"
github_name = input("Github Username: ")
github_pass = input("Github Password: ")
github_auth = requests.auth.HTTPBasicAuth(github_name, github_pass)

print("Parsing Repositories...")
repos = requests.get(github_api+"user/repos", auth=github_auth)
repos.raise_for_status()
repos = repos.json()
for i, repo in enumerate(repos):
    print(str(i)+": "+repo['full_name'])
repo = repos[int(input("Select repo: "))]

print("Creating labels...")
for label in labels:
    post_data = {
        "name": label['name'],
        "color": label['color'][1:]  # Remove leading '#' symbol
    }
    r = requests.post(github_api+"repos/"+repo['full_name']+"/labels",
                      auth=github_auth, data=json.dumps(post_data))
    print(r.text)

print("Creating issues and comments...")
for issue in issues:
    print("Creating issue "+issue['title'])
    post_data = {
        "title": issue['title'],
        "body": issue['description']+" \r\ncreated by @"+issue['author']['username'],
        "labels": issue['labels'],
    }
    if issue['assignee'] is not None:
        post_data['assignee'] = issue['assignee']['username']

    skip_issue = False
    while True:
        resp = requests.post(github_api+"repos/"+repo['full_name']+"/issues",
                            auth=github_auth, data=json.dumps(post_data)).json()
        print(resp)
        if 'errors' in resp:
            if resp['errors'][0]['field'] == 'assignee':
                print("Error occurred (Assignee validation error), retrying")
                del post_data['assignee']
            else:
                skip_issue = True
                break
        else:
            break
    if skip_issue is True:
        print("Skipping issue: Unknown Error")
        continue

    issue_number = resp['number']
    for comment in issue['comments']:
        post_data = {
            "body": comment['body']+" \r\ncreated by @"+comment['author']['username']
        }
        r = requests.post(github_api+"repos/"+repo['full_name']+"/issues/"+str(resp['number'])+"/comments",
                      auth=github_auth, data=json.dumps(post_data))
        print(r.text)
        time.sleep(1)  # Github will be angry if we're too fast
