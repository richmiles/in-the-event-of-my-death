import React, { useState, useRef, useCallback } from 'react'
import { useClickOutside } from '../hooks/useClickOutside'

interface Preset {
  value: string
  label: string
}

interface CollapsibleDateControlProps {
  id: string
  label: string
  displayValue: { date: string; time: string } | null
  presets: Preset[]
  activePreset: string
  onPresetChange: (preset: string) => void
  customDate: string
  customTime: string
  onCustomDateChange: (date: string) => void
  onCustomTimeChange: (time: string) => void
  minDate?: string
  customHint?: string
}

export function CollapsibleDateControl({
  id,
  label,
  displayValue,
  presets,
  activePreset,
  onPresetChange,
  customDate,
  customTime,
  onCustomDateChange,
  onCustomTimeChange,
  minDate,
  customHint,
}: CollapsibleDateControlProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const headerRef = useRef<HTMLButtonElement>(null)

  const collapse = useCallback(() => {
    setIsExpanded(false)
  }, [])

  useClickOutside(containerRef, collapse, isExpanded)

  const handleToggle = () => {
    setIsExpanded((prev) => !prev)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'Enter':
      case ' ':
        e.preventDefault()
        setIsExpanded((prev) => !prev)
        break
      case 'Escape':
        if (isExpanded) {
          setIsExpanded(false)
          headerRef.current?.focus()
        }
        break
    }
  }

  const showCustomInputs = activePreset === 'custom'

  return (
    <div className="date-control-wrapper" ref={containerRef}>
      <button
        type="button"
        className="date-control-header"
        ref={headerRef}
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        aria-expanded={isExpanded}
        aria-controls={`${id}-controls`}
      >
        <span className="date-control-label" id={`${id}-label`}>
          {label}:
        </span>
        <span className="date-control-value">
          {displayValue ? `${displayValue.date} at ${displayValue.time}` : 'Not set'}
        </span>
        <span className={`toggle-indicator ${isExpanded ? 'expanded' : ''}`} aria-hidden="true">
          <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
            <path
              d="M1 1L5 5L9 1"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      </button>

      <div
        id={`${id}-controls`}
        className={`collapsible-controls ${isExpanded ? 'expanded' : ''}`}
        role="region"
        aria-labelledby={`${id}-label`}
      >
        <div className="date-presets">
          {presets.map((preset) => (
            <button
              key={preset.value}
              type="button"
              className={activePreset === preset.value ? 'active' : ''}
              onClick={() => onPresetChange(preset.value)}
            >
              {preset.label}
            </button>
          ))}
        </div>

        {showCustomInputs && (
          <div className="custom-date-row">
            <div className="form-group">
              <label htmlFor={`${id}-custom-date`}>Date</label>
              <input
                type="date"
                id={`${id}-custom-date`}
                value={customDate}
                onChange={(e) => onCustomDateChange(e.target.value)}
                min={minDate}
              />
            </div>
            <div className="form-group">
              <label htmlFor={`${id}-custom-time`}>Time</label>
              <input
                type="time"
                id={`${id}-custom-time`}
                value={customTime}
                onChange={(e) => onCustomTimeChange(e.target.value)}
              />
            </div>
          </div>
        )}

        {showCustomInputs && !customDate && customHint && (
          <p className="field-hint">{customHint}</p>
        )}
      </div>
    </div>
  )
}
