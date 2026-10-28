const USERNAME_PATTERN = /^[a-zа-яё0-9_-]+$/

export interface LoginFormValues {
  username: string
  password: string
}

export interface RegisterFormValues {
  username: string
  display_name: string
  password: string
}

export function validateLoginForm(values: LoginFormValues): Partial<Record<keyof LoginFormValues, string>> {
  const errors: Partial<Record<keyof LoginFormValues, string>> = {}

  if (values.username.trim() === '') {
    errors.username = 'Username is required'
  } else if (values.username.length > 32) {
    errors.username = 'Username must be at most 32 characters'
  }

  if (values.password.trim() === '') {
    errors.password = 'Password is required'
  } else if (values.password.length < 8 || values.password.length > 128) {
    errors.password = 'Password must be 8 to 128 characters'
  }

  return errors
}

export function validateRegisterForm(
  values: RegisterFormValues,
): Partial<Record<keyof RegisterFormValues, string>> {
  const errors: Partial<Record<keyof RegisterFormValues, string>> = {}

  if (values.username.trim() === '') {
    errors.username = 'Username is required'
  } else if (values.username.length > 32) {
    errors.username = 'Username must be at most 32 characters'
  } else if (!USERNAME_PATTERN.test(values.username)) {
    errors.username = 'Username contains invalid characters'
  }

  if (values.display_name.trim() === '') {
    errors.display_name = 'Display name is required'
  } else if (values.display_name.length > 100) {
    errors.display_name = 'Display name must be at most 100 characters'
  }

  if (values.password.trim() === '') {
    errors.password = 'Password is required'
  } else if (values.password.length < 8 || values.password.length > 128) {
    errors.password = 'Password must be 8 to 128 characters'
  }

  return errors
}
