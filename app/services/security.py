import uuid
import re


def generate_uuid() -> str:
	full_uuid = str(uuid.uuid4()).replace('-', '').lower()
	return full_uuid

def generate_otp() -> str:
	full_uuid = generate_uuid()
	otp = f"{full_uuid[:4]}-{full_uuid[-2:]}".upper()
	return otp

def generate_id() -> str:
    new_uuid = generate_uuid()
    return f"{new_uuid[-19:]}.{new_uuid[:12]}"

def generate_short_id() -> str:
	full_uuid = generate_uuid()
	short_id = full_uuid[:12]
	return f"{short_id}"


def generate_prefixed_id(prefix: str) -> str:
    new_uuid = generate_uuid()
    return f"{prefix.lower()}.{new_uuid[16:]}{new_uuid[:8]}"


def generate_username(fn:str, mn:str, ln: str):
	if mn:
		initials = fn[0] + mn[0]
	else:
		initials = fn[:2]
	return f"{initials.lower()}.{re.sub(r'[- ]', '', ln)}@phinma.ui"


def generate_default_password(fn: str, mn: str, ln: str):
    if not fn or not ln:
        raise ValueError("First name and last name cannot be empty.")

    if mn:
        initials = fn[0] + mn[0]
    else:
        initials = fn[:2]

    name_part = (initials + ln).upper()

    return f"{name_part}@{generate_uuid()[:5]}" # Expected output: Joe Antiporda Gonzales >> ja.gonzales-X3F53


def censor_email(email: str) -> str:
    try:
        local, domain = email.split("@")
        domain_name, domain_ext = domain.rsplit(".", 1)
        
        def mask(part: str) -> str:
            if len(part) <= 2:
                return part[0] + "*" * (len(part) - 1)
            return part[0] + "*" * (len(part) - 2) + part[-1]
        
        return f"{mask(local)}@{mask(domain_name)}.{domain_ext}"
    
    except ValueError:
        raise ValueError("Invalid email format")
