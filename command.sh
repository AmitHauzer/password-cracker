
# 1. start master server
python -m password_cracker.master.master_server
or 
python password_cracker/master/master_server.py

# 2. start minion server
python -m password_cracker.minion.minion_server --port 8001
or 
python password_cracker/minion/minion_server.py --port 8001

# 3. start minion server
python -m password_cracker.minion.minion_server --port 8002

# 4. start minion server
python -m password_cracker.minion.minion_server --port 8003

# 5. start minion server
python -m password_cracker.minion.minion_server --port 8004

# 6. start minion server
python -m password_cracker.minion.minion_server --port 8005

# 7. start minion server
python -m password_cracker.minion.minion_server --port 8006



# send request to master server
curl -X POST http://localhost:8000/crack -H "Content-Type: application/json" -d '{"hash": "1a1674fc1f2ce010f161b4cd1ad80939"}'

curl -X POST http://localhost:8000/crack -H "Content-Type: application/json" -d '{"hash": "709163141b3d03bf79603309e8d8086e"}'


# send request to minion server with file

curl -X POST http://localhost:8000/upload-hashes   -F "file=@password_cracker/hashes.txt"

