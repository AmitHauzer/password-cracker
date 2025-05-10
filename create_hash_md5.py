
import hashlib


def get_hash(phone_number):
    hash_obj = hashlib.md5(phone_number.encode())
    return hash_obj.hexdigest()


print(get_hash("050-0000005"))
print(get_hash("050-0000000"))
print(get_hash("050-0001000"))
print(get_hash("059-9999999"))
