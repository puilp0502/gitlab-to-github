import json
import time
import getpass

import gitlab
import requests
import requests.auth


def main():
    host = input("Gitlab Host (https://gitlab.com/): ")

    if host == '':
        host = 'https://gitlab.com/'

    token = getpass.getpass("Private Token: ")
    gl = gitlab.Gitlab(host, private_token=token)

    print("Parsing Projects...")
    projects = gl.projects.list(membership=1)
    projects += gl.projects.list(owned=1)

    for i, project in enumerate(projects):
        print('[%d] %s' % (i, project.name_with_namespace))
    project = projects[int(input("Select project: "))]

    print("Parsing Issues...")
    issues = project.issues.list(order_by='created_at', sort='asc')
    for issue in issues: print(issue.title)

    print("Parsing labels...")
    labels = project.labels.list()
    print([l.name for l in labels])

    print("Parsing comments...")
    for i, issue in enumerate(issues):
        print("{}: {} (ID {})".format(i+1, issue.title, issue.id))
        issue.notes_local = issue.notes.list(sort='asc')

    github_api = "https://api.github.com/"
    github_name = input("Github Username: ")
    github_pass = getpass.getpass("Github Password: ")
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
            time.sleep(0.5)  # Github will be angry if we're too fast

if __name__ == "__main__":
    main()
