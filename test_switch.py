import subprocess
prev = subprocess.check_output(["SwitchAudioSource", "-c", "-t", "output"]).decode().strip()
print("Prev:", prev)
subprocess.run(["SwitchAudioSource", "-t", "output", "-s", "reSpeaker XVF3800 4-Mic Array"], check=True)
curr = subprocess.check_output(["SwitchAudioSource", "-c", "-t", "output"]).decode().strip()
print("Curr:", curr)
subprocess.run(["SwitchAudioSource", "-t", "output", "-s", prev], check=True)
