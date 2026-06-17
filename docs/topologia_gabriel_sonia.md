# Topología SSH — Gabriel & Sonia

## Equipos

| Usuario | Máquina | IP Tailscale |
|---|---|---|
| `gabriel` | `actuary` | `100.125.31.35` |
| `sonia` | `envy` | `100.112.41.4` |
| `gabriel` | `envy` | `100.112.41.4` |

Los equipos están conectados mediante **VPN Tailscale**.

---

## Conexiones SSH directas

```bash
ssh gabriel@100.125.31.35   # gabriel@actuary
ssh sonia@100.112.41.4      # sonia@envy
ssh gabriel@100.112.41.4    # gabriel@envy
```

Los alias `gabriel` y `sonia` están configurados para conectarse desde el equipo contrario:

- **`sonia`** — desde `gabriel@actuary`, abre sesión en `sonia@envy`
- **`gabriel`** — desde `gabriel@envy`, abre sesión en `gabriel@actuary`

---

## Montajes

### `--bind` entre `gabriel@envy` y `sonia@envy`

Montar el directorio de Sonia en el espacio de trabajo de Gabriel (mismo equipo, usuarios distintos):

```bash
sudo mount --bind /home/sonia/boutique_zepeda/pto_montaje \
                  /home/gabriel/boutique_zepeda/pto_montaje
```

Desmontar:

```bash
sudo umount /home/gabriel/boutique_zepeda/pto_montaje
```

---

### `monta_actuary` — desde `gabriel@envy` hacia `gabriel@actuary`

Monta vía SSHFS el directorio de insumos de ML en `actuary` dentro del equipo `envy`:

```bash
sshfs gabriel@100.125.31.35:/home/gabriel/research/insumos_ML-for-Insurance \
      ~/research/insumos_ML-for-Insurance \
      -o reconnect \
      -o ServerAliveInterval=15 \
      -o ServerAliveCountMax=3 \
      -o IdentityFile=~/.ssh/id_ed25519 \
      -o allow_other \
      -o default_permissions
```

Verificar el montaje:

```bash
df -h | grep insumos
ls ~/research/insumos_ML-for-Insurance
```

Desmontar:

```bash
fusermount -u ~/research/insumos_ML-for-Insurance
```

---

### `monta_sonia` — desde `gabriel@actuary` hacia `sonia@envy`

Monta vía SSHFS el punto de montaje de Sonia en `actuary`:

```bash
alias monta_sonia='sshfs sonia@100.112.41.4:/home/sonia/boutique_zepeda/pto_montaje \
      ~/boutique_zepeda/pto_montaje \
      -o reconnect \
      -o ServerAliveInterval=15 \
      -o ServerAliveCountMax=3 \
      -o IdentityFile=~/.ssh/id_ed25519 \
      -o allow_other \
      -o default_permissions'
```

Desmontar:

```bash
fusermount -u ~/boutique_zepeda/pto_montaje
```

---

## Aislamiento SSH (`aislar_@actuary`)

Alias disponibles para gestionar el aislamiento de conexiones desde `actuary`:

| Alias | Comportamiento |
|---|---|
| `aislar` | Modo interactivo |
| `aislar_ya` | Limpia todas las conexiones sin confirmar |
| `aislar --check` | Solo revisa el estado, sin modificar nada |
