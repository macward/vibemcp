# Ideas de Componentes

## Auth Components

- [ ] LoginForm — formulario de login con validación
- [ ] RegisterForm — registro con confirmación de password
- [ ] ForgotPassword — reset de password por email
- [ ] SocialLogin — botones de OAuth (Google, GitHub)

## Dashboard Components

- [ ] Sidebar — navegación lateral collapsible
- [ ] Header — user menu, notifications
- [ ] StatCard — tarjeta de estadística con icono
- [ ] ActivityFeed — lista de actividad reciente

## Ideas sueltas

Pensar en hacer los forms totalmente genéricos con un schema-driven approach:

```tsx
const schema = {
  fields: [
    { name: 'email', type: 'email', required: true },
    { name: 'password', type: 'password', min: 8 }
  ]
};

<DynamicForm schema={schema} onSubmit={handleSubmit} />
```

Puede ser overengineering, evaluar después.
