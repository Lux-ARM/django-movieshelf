"""Corrige tous les == sans espaces dans les templates Django."""
import os

FIXES = [
    ("statut=='a_voir'", "statut == 'a_voir'"),
    ("statut=='vu'", "statut == 'vu'"),
    ("statut=='favori'", "statut == 'favori'"),
    ("genre==g.slug", "genre == g.slug"),
]

for root, dirs, files in os.walk('.'):
    for name in files:
        if name.endswith('.html'):
            path = os.path.join(root, name)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            original = content
            for old, new in FIXES:
                content = content.replace(old, new)
            if content != original:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f'FIXED: {path}')
print('DONE')
