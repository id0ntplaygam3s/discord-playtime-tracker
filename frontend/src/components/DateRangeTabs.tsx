import { DateRangeKey } from '../types';

type DateRangeOption = {
  key: DateRangeKey;
  label: string;
};

interface DateRangeTabsProps {
  options: DateRangeOption[];
  value: DateRangeKey;
  onChange: (key: DateRangeKey) => void;
  ariaLabel: string;
}

export default function DateRangeTabs({ options, value, onChange, ariaLabel }: DateRangeTabsProps) {
  return (
    <div className="date-range-tabs" role="tablist" aria-label={ariaLabel}>
      {options.map((option) => {
        const isActive = value === option.key;
        return (
          <button
            key={option.key}
            type="button"
            role="tab"
            aria-selected={isActive}
            className={`range-tab ${isActive ? 'range-tab-active' : ''}`}
            onClick={() => onChange(option.key)}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
