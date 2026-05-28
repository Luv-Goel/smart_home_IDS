with open('ids-monorepo/.github/workflows/build.yml', 'r') as f:
    content = f.read()

content = content.replace(' _arm64-compatibility:', '  arm64-compatibility:')

with open('ids-monorepo/.github/workflows/build.yml', 'w') as f:
    f.write(content)
