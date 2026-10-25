import { useState, useMemo, type ChangeEvent } from 'react';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  ariaLabel?: string;
}

export function SearchInput({ value, onChange, placeholder = 'Search...', ariaLabel = 'Search' }: SearchInputProps) {
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value);
  };

  return (
    <input
      type="search"
      value={value}
      onChange={handleChange}
      placeholder={placeholder}
      aria-label={ariaLabel}
      className="search-input"
    />
  );
}

export function useSearch<T extends Record<string, unknown>>(
  items: T[],
  searchFields: (keyof T)[],
  initialValue = ''
) {
  const [query, setQuery] = useState(initialValue);

  const filtered = useMemo(() => {
    if (!query.trim()) return items;
    const lowerQuery = query.toLowerCase();
    return items.filter((item) =>
      searchFields.some((field) => {
        const value = item[field];
        return value != null && String(value).toLowerCase().includes(lowerQuery);
      })
    );
  }, [items, query, searchFields]);

  return { query, setQuery, filtered };
}
