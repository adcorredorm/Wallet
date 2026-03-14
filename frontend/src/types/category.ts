/**
 * Category type definitions
 * Represents income/expense categories with optional hierarchy
 */

export enum CategoryType {
  INCOME = 'income',
  EXPENSE = 'expense',
  BOTH = 'both'
}

export interface Category {
  id: string
  name: string
  type: CategoryType
  icon?: string
  color?: string  // Hex color code (#RRGGBB)
  parent_category_id?: string
  active: boolean
  created_at: string
  updated_at: string
}

export interface CreateCategoryDto {
  name: string
  type: CategoryType
  icon?: string
  color?: string
  parent_category_id?: string
}

export interface UpdateCategoryDto {
  name?: string
  type?: CategoryType
  icon?: string
  color?: string
  parent_category_id?: string
  active?: boolean
}
