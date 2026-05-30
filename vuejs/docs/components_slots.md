# Slots в компонентах Vue

Этот справочник собрал все базовые практики по slots: обычный slot, именованные slots и scoped slots (передача данных в slot).

## Контент через slot

`slot` позволяет передать разметку внутрь дочернего компонента.

### Дочерний компонент

```vue
<template>
  <section class="card">
    <h3>Профиль</h3>
    <slot />
  </section>
</template>
```

### Родитель

```vue
<template>
  <ProfileCard>
    <p>Текст внутри слота</p>
  </ProfileCard>
</template>
```

- `slot` делает компонент гибким без жесткой привязки к одному шаблону.
- Для сложных случаев используйте именованные и scoped slots.

## Именованные slots

Именованные слоты полезны, когда у компонента несколько зон вставки: например header, body и footer.

### Дочерний компонент

```vue
<template>
  <article class="panel">
    <header>
      <slot name="header">Заголовок по умолчанию</slot>
    </header>

    <main>
      <slot />
    </main>

    <footer>
      <slot name="footer" />
    </footer>
  </article>
</template>
```

### Родитель

```vue
<template>
  <BasePanel>
    <template #header>
      <h2>Пользователь</h2>
    </template>

    <p>Основной контент</p>

    <template #footer>
      <button>Сохранить</button>
    </template>
  </BasePanel>
</template>
```

- Используйте `#header` как короткую форму `v-slot:header`.
- Давайте слотам понятные имена по роли, а не по внешнему виду.

## Scoped slots (передача данных в slot)

Scoped slot нужен, когда дочерний компонент передает данные в разметку родителя.

### Дочерний компонент

```vue
<template>
  <ul>
    <li v-for="user in users" :key="user.id">
      <slot name="item" :user="user" :is-active="user.isActive">
        {{ user.name }}
      </slot>
    </li>
  </ul>
</template>

<script setup>
const users = [
  { id: 1, name: 'Alex', isActive: true },
  { id: 2, name: 'Mira', isActive: false },
]
</script>
```

### Родитель

```vue
<template>
  <UsersList>
    <template #item="{ user, isActive }">
      <strong :class="{ active: isActive }">{{ user.name }}</strong>
    </template>
  </UsersList>
</template>
```

- Передавайте в scoped slot только то, что реально используется.
- Имена slot props должны отражать смысл данных.
- Держите fallback-контент в дочернем компоненте для надежности.

## Практические советы

- Проектируйте slots как часть публичного API компонента.
- Не перегружайте slot props: передавайте только нужный минимум.
- Если слотов много и они обязательны, явно документируйте их назначение в README компонента.
