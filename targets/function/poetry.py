import platform
import shutil
import subprocess
import os

def add_plugins():
  cmds = []
  cmds.append(['poetry', '-q', 'self', 'add', 'poetry-bumpversion'])
  cmds.append(['poetry', '-q', 'self', 'add', 'poetry-plugin-export'])
  cmds.append(['poetry', '-q', 'self', 'add', 'update'])
  for cmd in cmds:
    subprocess.run(cmd, text=True, check=True, stderr=subprocess.STDOUT)

def start_function():
  add_plugins
  cmds = []
  cmds.append(['poetry', '-q', 'export', '-f', 'requirements.txt', '--without-hashes', '-o', 'requirements.txt'])
  if platform.system() == "Linux" or platform.system() == "Darwin":
    azurite_data_dir = os.environ.get('HOME') + '/.local/share/azurite'
  elif platform.system() == "Windows":
    azurite_data_dir = os.environ.get('APPDATA').replace('\\', '/').lower() + '/azurite'
  if not os.path.exists(azurite_data_dir):
    os.makedirs(azurite_data_dir)
  azurite_stop = False
  if not subprocess.run(
      ['docker', 'ps', '-f', 'name=azurite', '--format', '{{.Names}}'],
      text=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    ).stdout:
    cmds.append([
      'docker', 'run', '-d', '--rm', '--name', 'azurite', '-v', azurite_data_dir + ':/data',
      '-p', '10000:10000', '-p', '10001:10001', '-p', '10002:10002', 'mcr.microsoft.com/azure-storage/azurite'
    ])
    azurite_stop = True
  for cmd in cmds:
    subprocess.run(cmd, text=True, check=True, stderr=subprocess.STDOUT)
  try:
    subprocess.run(['func', 'start'], text=True, check=True, stderr=subprocess.STDOUT)
  except:
    if azurite_stop:
      azurite_stop = subprocess.run(
        ['docker', 'stop', 'azurite'], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
      )
      if azurite_stop.returncode != 0:
        print(azurite_stop.stdout)
    exit(1)

def build():
  add_plugins
  cmds = []
  cmds.append(['pip', 'install', '-q', '--upgrade', 'pip'])
  cmds.append(['pip', 'install', '-q', '--target=./.python_packages/lib/site-packages', '-r', 'requirements.txt'])
  cmds.append(['poetry', 'build', '-f', 'sdist'])
  for cmd in cmds:
    subprocess.run(cmd, text=True, check=True, stderr=subprocess.STDOUT)
  shutil.rmtree('./.python_packages')

  # Build zip archive on Linux and MacOS
  if platform.system() == "Linux" or platform.system() == "Darwin":
    pkg = subprocess.run(
      ['poetry', 'version'], text=True, check=True,
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    ).stdout.split(' ')
    pkg = '-'.join([pkg[0].replace('-', '_'), pkg[1].lower()]).strip()
    subprocess.run(
      ['tar', '-xzf', pkg + '.tar.gz'], cwd='./dist',
      text=True, check=True, stderr=subprocess.STDOUT
    )
    subprocess.run(
      ['zip', '-qr', '../' + pkg + '.zip', '.'], cwd='./dist/' + pkg,
      text=True, check=True, stderr=subprocess.STDOUT 
    )
    print('  - Built \033[0;32m' + pkg + '.zip\033[0m')
    shutil.rmtree('./dist/' + pkg)

def test():
  cmds = []
  cmds.append(['poetry', '-q', 'install', '--with', 'test', '--sync'])
  cmds.append(['pytest', '-v', '--doctest-modules', '--junitxml=junit/test-results.xml', '--cov=.', '--cov-report=xml'])
  for cmd in cmds:
    subprocess.run(cmd, text=True, check=True, stderr=subprocess.STDOUT)
