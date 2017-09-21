import requests
import json
import logging
import maskgen
import wget
from subprocess import Popen, PIPE

"""
Git API used to compare version of the tool with lastest on GitHub master
"""

class UpdaterGitAPI:

    file = 'https://raw.githubusercontent.com/rwgdrummer/maskgen/master/VERSION'
    #file = 'https://raw.githubusercontent.com/rwgdrummer/maskgen/VersionScanner/VERSION'
    repos = 'rwgdrummer/maskgen'
    url = 'https://api.github.com/repos'
    zip = 'https://github.com/' + repos + '/archive/master.zip'

    def __init__(self):
        pass

    def _get_version_file(self):
        resp = requests.get(self.file)
        if resp.status_code == requests.codes.ok:
            return  resp.content.strip()

    def _get_tag(self):
        url =  self.url + '/' + self.repos + '/tags'
        resp = requests.get(url)
        if resp.status_code == requests.codes.ok:
            content = json.loads(resp.content)
            content[0]['name']

    def _getCommitMessage(self, sha):
        url = self.url + '/' + self.repos + '/commits/' + sha
        resp = requests.get(url)
        if resp.status_code == requests.codes.ok:
            content = json.loads(resp.content)
            return content['commit']['message']
        return None

    def _parseCommits(self, content):
        for item in  content:
            if 'merged_at' in item and 'merge_commit_sha' in item:
                return  item['merge_commit_sha']
        return None

    def _hasNotPassed(self,  merge_sha):
        if merge_sha is None:
            return True
        currentversion = maskgen.__version__
        sha = currentversion[currentversion.rfind('.')+1:]
        return not merge_sha.startswith(sha)
        #if lasttime is not None and merge_time is not None:
           # lasttimeval = datetime.strptime(lasttime, '%Y-%m-%dT%H:%M:%SZ')
           # mergetimeval = datetime.strptime(merge_time, '%Y-%m-%dT%H:%M:%SZ')
           # d  =  mergetimeval - lasttimeval
           # if d.total_seconds() > 0:
           #     return True
        #return False

    def _get_lastcommit(self):
        url = self.url + '/' + self.repos + '/pulls?state=closed'
        resp = requests.get(url)
        if resp.status_code == requests.codes.ok:
            content = json.loads(resp.content)
            return self._parseCommits(content)

    def isOutdated(self):
        merge_sha = self._get_version_file()
        if self._hasNotPassed( merge_sha):
            return (merge_sha, self._getCommitMessage(merge_sha))
        return None,None

    def update(self):
        import zipfile
        import sys
        import os
        import platform
        if os.path.exists('maskgen-master.zip'):
            os.remove('maskgen-master.zip')
        wget.download(self.zip)
        places =[place for place in sys.path if
                               place.endswith('maskgen-master') and os.path.exists(os.path.join(place, 'scripts'))]
        if len(places) == 0:
            raise ValueError("Maskgen not installed zip file")
        place  = places[1]
        with zipfile.ZipFile('maskgen-master.zip') as myzip:
            myzip.extractall(path=os.path.split(place)[0])
        if sys.platform.startswith('win'):
            command = 'update_dos.bat'
        else:
            command = 'update_unix.sh'
        p = Popen([os.path.join(place, 'scripts' + os.sep + command)], stderr=PIPE, stdout=PIPE, shell=True)
        results = p.communicate()
        for result in results:
            print str(result)
        os.execv(__file__, sys.argv)
        os.path.exit(0)
