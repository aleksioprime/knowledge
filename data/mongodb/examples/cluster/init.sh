#!/usr/bin/env bash
# Инициализация кластера. Повторный запуск безопасен: уже сделанные шаги пропускаются.
set -euo pipefail

wait_for() {
  until mongosh --quiet --host "$1" --eval 'db.adminCommand({ping: 1}).ok' >/dev/null 2>&1; do
    echo "жду $1..."; sleep 1
  done
}

# Инициализирует репликасет, если он ещё не создан, и ждёт выбора primary
init_rs() {
  local host=$1 config=$2
  wait_for "$host"
  mongosh --quiet --host "$host" --eval "
    try { rs.status() } catch (e) { rs.initiate($config) }
    while (!db.hello().isWritablePrimary) { sleep(500) }
    print('$host: primary готов')
  "
}

init_rs cfg:27017 '{_id: "cfgrs", configsvr: true, members: [{_id: 0, host: "cfg:27017"}]}'
init_rs shard1a:27017 '{_id: "rs1", members: [{_id: 0, host: "shard1a:27017", priority: 2}]}'
init_rs shard2a:27017 '{_id: "rs2", members: [{_id: 0, host: "shard2a:27017"}]}'

# Профиль replica: добавляем в rs1 две secondary-ноды
for node in shard1b shard1c; do
  if getent hosts "$node" >/dev/null; then
    wait_for "$node:27017"
    mongosh --quiet --host "rs1/shard1a:27017" --eval "
      if (!rs.conf().members.some(m => m.host === '$node:27017')) rs.add('$node:27017')
      print('rs1:', rs.conf().members.map(m => m.host).join(', '))
    "
  fi
done

wait_for mongos:27017
mongosh --quiet --host mongos:27017 --eval '
  const shards = db.adminCommand({listShards: 1}).shards.map(s => s._id)
  if (!shards.includes("rs1")) sh.addShard("rs1/shard1a:27017")
  if (!shards.includes("rs2")) sh.addShard("rs2/shard2a:27017")
  // Маленький размер чанка (1 МБ вместо 128), чтобы балансировщик было видно на учебных объёмах
  db.getSiblingDB("config").settings.updateOne({_id: "chunksize"}, {$set: {value: 1}}, {upsert: true})
  print("шарды:", db.adminCommand({listShards: 1}).shards.map(s => s._id).join(", "))
'
