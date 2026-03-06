# dotbot-age

A [dotbot](https://github.com/anishathalye/dotbot) plugin for decrypting [age](https://github.com/FiloSottile/age)-encrypted secrets and rendering templates into your dotfiles.

## Why

Dotfiles repos often need secrets — SSH configs, API keys, AWS credentials. You want them version-controlled but encrypted. This plugin adds a `decrypt` directive to dotbot that:

- Decrypts an age-encrypted `KEY=VALUE` file
- Renders templates with `{{PLACEHOLDER}}` substitution
- Outputs to a private directory (gitignored)
- Sets proper permissions (700 dirs, 600 files)
- Supports `--dry-run`
- Is idempotent (skips unchanged files)

## How it works

Dotbot symlinks (e.g. `~/.ssh/config`) point to files in `private/`. These files are rendered from templates in `encrypted/` by substituting `{{PLACEHOLDERS}}` with values from the encrypted secrets file.

When you run `./edit-secrets`, the script re-encrypts your changes and immediately re-renders the templates into `private/`. Since the symlinks already point there, your tools pick up the new values right away — no need to re-run `./install`.

`./install` is only needed when you add new symlinks or set up a new machine.

## Prerequisites

Install [age](https://github.com/FiloSottile/age):

```bash
# macOS
brew install age

# Linux
apt install age  # or see https://github.com/FiloSottile/age#installation
```

## Setup

### 1. Add the plugin as a submodule

```bash
git submodule add https://github.com/fcatuhe/dotbot-age.git
```

### 2. Gitignore private files

Add to your `.gitignore`:

```
encrypted/age.key
private/
```

### 3. Copy the edit-secrets script

```bash
cp dotbot-age/tools/edit-secrets .
```

### 4. Generate an age identity

```bash
mkdir -p encrypted
age-keygen -o encrypted/age.key
```

### 5. Create templates

Create template files in subdirectories of `encrypted/` using `{{PLACEHOLDER}}` syntax:

```
encrypted/
├── age.key              # gitignored
├── secrets.env.age      # committed (encrypted)
├── ssh/
│   └── config           # template
└── aws/
    └── config           # template
```

Example `encrypted/ssh/config`:

```
Host myserver
  HostName {{SSH_SERVER_IP}}
  User {{SSH_SERVER_USER}}
  IdentityFile ~/.ssh/id_ed25519
```

### 6. Create your secrets file

```bash
./edit-secrets
```

This opens your `$EDITOR` with a `KEY=VALUE` file. Add your secrets:

```env
SSH_SERVER_IP=192.168.1.100
SSH_SERVER_USER=admin
AWS_ACCOUNT_ID=123456789
API_KEY=sk-secret-key
```

On save, the file is encrypted to `encrypted/secrets.env.age` and templates are automatically re-rendered into `private/`.

### 7. Configure dotbot

In your `install.conf.yaml`:

```yaml
- plugins:
    - dotbot-age

- decrypt: true

- link:
    ~/.ssh/config: private/ssh/config
    ~/.aws/config: private/aws/config
```

## Convention

The plugin works with zero configuration if you follow these conventions:

| Path | Purpose |
| --- | --- |
| `encrypted/age.key` | Age identity (private key, gitignored) |
| `encrypted/secrets.env.age` | Encrypted `KEY=VALUE` secrets (committed) |
| `encrypted/*/` | Template files with `{{PLACEHOLDERS}}` |
| `private/` | Rendered output (gitignored, created by plugin) |

All conventions can be overridden:

```yaml
- decrypt:
    key: path/to/identity.key
    vars: path/to/secrets.env.age
    encrypted: path/to/templates/
    private: path/to/output/
```

## Workflow

### New machine

```bash
git clone <your-dotfiles-repo> ~/.dotfiles
cd ~/.dotfiles
# Copy age.key from a secure location (password manager, USB key, etc.)
cp /secure/location/age.key encrypted/age.key
./install
```

### Edit secrets

```bash
./edit-secrets
```

That's it — templates are re-rendered automatically. No need to run `./install`.

### Add a new template

1. Create a file in `encrypted/<category>/<filename>` with `{{PLACEHOLDERS}}`
2. Add the corresponding link in `install.conf.yaml`: `~/.config/thing: private/<category>/<filename>`
3. Run `./install`

## License

This software is released under the MIT License.
