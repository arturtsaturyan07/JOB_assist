key = open('azduna_api_key.txt').read().strip()
parts = key.split(':')
print(f'Parts: {len(parts)}')
print(f'Key content: {key}')
if len(parts) > 1:
    print(f'Part 1: {parts[0]}')
    print(f'Part 2: {parts[1]}')
else:
    print(f'Single part: {parts[0]}')
