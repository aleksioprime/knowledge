# Поиск, фильтрация и сортировка во Vue

Для локального списка исходные данные хранят в `ref`, выбранные условия — в отдельных реактивных переменных, а итоговый список получают через `computed`. При изменении поисковой строки, категории или сортировки Vue автоматически пересчитает результат.

## Полный пример

```vue
<script setup>
import { computed, ref } from 'vue'

// Исходный список обычно приходит из API и не изменяется при фильтрации.
const products = ref([
  { id: 1, title: 'Ноутбук', category: 'Техника', price: 95000 },
  { id: 2, title: 'Клавиатура', category: 'Техника', price: 7000 },
  { id: 3, title: 'Vue.js в действии', category: 'Книги', price: 1800 },
  { id: 4, title: 'JavaScript. Подробное руководство', category: 'Книги', price: 3200 },
])

// Состояние элементов управления списком.
const search = ref('')
const selectedCategory = ref('')
const sortBy = ref('title-asc')

// Collator корректно сравнивает русские строки, регистр и числа в названиях.
const collator = new Intl.Collator('ru', {
  sensitivity: 'base',
  numeric: true,
})

// Собираем уникальные категории из загруженных товаров.
const categories = computed(() => {
  const uniqueCategories = new Set(products.value.map((product) => product.category))
  return [...uniqueCategories].sort(collator.compare)
})

// Итоговый список зависит от товаров и всех выбранных условий.
const visibleProducts = computed(() => {
  // Нормализация делает поиск независимым от регистра и крайних пробелов.
  const query = search.value.trim().toLocaleLowerCase('ru-RU')

  const filteredProducts = products.value.filter((product) => {
    const matchesSearch = product.title
      .toLocaleLowerCase('ru-RU')
      .includes(query)

    const matchesCategory = selectedCategory.value === ''
      || product.category === selectedCategory.value

    // Товар должен одновременно пройти поиск и фильтр категории.
    return matchesSearch && matchesCategory
  })

  // sort() изменяет массив, поэтому сортируем копию результата.
  return [...filteredProducts].sort((first, second) => {
    switch (sortBy.value) {
      case 'title-desc':
        return collator.compare(second.title, first.title)
      case 'price-asc':
        return first.price - second.price
      case 'price-desc':
        return second.price - first.price
      default:
        return collator.compare(first.title, second.title)
    }
  })
})

function resetFilters() {
  // Возвращаем все элементы управления к начальному состоянию.
  search.value = ''
  selectedCategory.value = ''
  sortBy.value = 'title-asc'
}
</script>

<template>
  <section>
    <!-- Все значения связаны с реактивным состоянием через v-model. -->
    <div class="filters">
      <label>
        Поиск
        <input v-model="search" type="search" placeholder="Название товара">
      </label>

      <label>
        Категория
        <select v-model="selectedCategory">
          <option value="">Все категории</option>
          <option
            v-for="category in categories"
            :key="category"
            :value="category"
          >
            {{ category }}
          </option>
        </select>
      </label>

      <label>
        Сортировка
        <select v-model="sortBy">
          <option value="title-asc">Название: А–Я</option>
          <option value="title-desc">Название: Я–А</option>
          <option value="price-asc">Сначала дешевле</option>
          <option value="price-desc">Сначала дороже</option>
        </select>
      </label>

      <button type="button" @click="resetFilters">Сбросить</button>
    </div>

    <p>Найдено: {{ visibleProducts.length }}</p>

    <!-- В шаблон передаётся уже подготовленный computed-список. -->
    <div v-if="visibleProducts.length">
      <article v-for="product in visibleProducts" :key="product.id">
        <h2>{{ product.title }}</h2>
        <p>{{ product.category }} · {{ product.price }} ₽</p>
      </article>
    </div>

    <p v-else>По заданным условиям ничего не найдено.</p>
  </section>
</template>
```

## Как работает обработка списка

Вычисляемое свойство `visibleProducts` последовательно:

1. нормализует поисковую строку;
2. оставляет товары с подходящим названием и категорией;
3. создаёт копию отфильтрованного массива;
4. сортирует копию выбранным способом.

`computed` кэширует результат и пересчитывает его только после изменения зависимостей: `products`, `search`, `selectedCategory` или `sortBy`. Для получения производного списка `watch` не нужен.

`Intl.Collator` сравнивает строки с учётом языка. Это надёжнее простого сравнения `first.title > second.title`, особенно для кириллицы, регистра и чисел внутри названий.

## Почему перед `sort()` создаётся копия

Метод `sort()` изменяет исходный массив. Мутировать `products` внутри `computed` не следует: это меняет источник данных и может приводить к неожиданному порядку элементов в других частях приложения.

```js
// Неправильно: изменяет исходный массив
return products.value.sort(compareProducts)

// Правильно: сортирует копию
return [...products.value].sort(compareProducts)
```

Метод `filter()` сам возвращает новый массив, но явная копия перед сортировкой делает намерение понятным и не зависит от предыдущих шагов обработки.

## Категории из API

Если категории уже приходят отдельным справочником, используйте его вместо вычисления из списка товаров:

```js
const categories = ref([])

async function loadCategories() {
  // Отдельный endpoint возвращает полный справочник категорий.
  const response = await apiClient.get('/api/v1/categories')
  categories.value = response.data
}
```

Это особенно важно при серверной пагинации: текущая страница товаров может содержать не все существующие категории.

## Когда фильтровать на сервере

Локальная обработка подходит, если весь список уже загружен и имеет небольшой размер. Для большого списка, пагинации или бесконечной прокрутки условия нужно передавать backend:

```js
// Backend применит условия до пагинации и вернёт только нужную страницу.
const response = await apiClient.get('/api/v1/products', {
  params: {
    search: search.value || undefined,
    category: selectedCategory.value || undefined,
    ordering: sortBy.value,
  },
})
```

Для поисковой строки при серверных запросах обычно применяют [debounce](debounce_throttle.md), чтобы запрос не отправлялся после каждого нажатия клавиши. Backend должен самостоятельно выполнять фильтрацию, сортировку и возвращать общее количество результатов.

## Практические рекомендации

- Используйте `computed` для производного локального списка и не перезаписывайте исходные данные.
- Не размещайте `v-if` и `v-for` на одном элементе; сначала подготовьте список в `computed`.
- Передавайте в `:key` стабильный идентификатор элемента, а не индекс массива.
- Храните в `sortBy` техническое значение (`price-desc`), а пользователю показывайте понятную подпись.
- Для сброса фильтров возвращайте все управляющие значения к явно заданному начальному состоянию.
- При поиске по нескольким полям объединяйте нормализованные значения или проверяйте каждое поле отдельно.

## Полезные ссылки

- [Вычисляемые свойства](https://vuejs.org/guide/essentials/computed.html)
- [Отображение отфильтрованных и отсортированных списков](https://vuejs.org/guide/essentials/list.html#displaying-filtered-sorted-results)
