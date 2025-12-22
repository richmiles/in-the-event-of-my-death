import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CollapsibleDateControl } from './CollapsibleDateControl'

describe('CollapsibleDateControl', () => {
  const defaultProps = {
    id: 'test-control',
    label: 'Unlock Date',
    displayValue: { date: 'Mon, Jan 1, 2025', time: '12:00 PM' },
    presets: [
      { value: '1w', label: '1 Week' },
      { value: '1m', label: '1 Month' },
      { value: 'custom', label: 'Custom' },
    ],
    activePreset: '1w',
    onPresetChange: vi.fn(),
    customDate: '',
    customTime: '',
    onCustomDateChange: vi.fn(),
    onCustomTimeChange: vi.fn(),
  }

  it('should render with label and display value', () => {
    render(<CollapsibleDateControl {...defaultProps} />)

    expect(screen.getByText('Unlock Date:')).toBeInTheDocument()
    expect(screen.getByText('Mon, Jan 1, 2025 at 12:00 PM')).toBeInTheDocument()
  })

  it('should display "Not set" when displayValue is null', () => {
    render(<CollapsibleDateControl {...defaultProps} displayValue={null} />)

    expect(screen.getByText('Not set')).toBeInTheDocument()
  })

  it('should expand when header is clicked', () => {
    render(<CollapsibleDateControl {...defaultProps} />)

    const header = screen.getByRole('button', { name: /Unlock Date/i })
    expect(header).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(header)
    expect(header).toHaveAttribute('aria-expanded', 'true')
  })

  it('should render preset buttons', () => {
    render(<CollapsibleDateControl {...defaultProps} />)

    // Expand to see presets
    fireEvent.click(screen.getByRole('button', { name: /Unlock Date/i }))

    expect(screen.getByRole('button', { name: '1 Week' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '1 Month' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Custom' })).toBeInTheDocument()
  })

  it('should call onPresetChange when preset button is clicked', () => {
    const onPresetChange = vi.fn()
    render(<CollapsibleDateControl {...defaultProps} onPresetChange={onPresetChange} />)

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /Unlock Date/i }))

    // Click a preset
    fireEvent.click(screen.getByRole('button', { name: '1 Month' }))

    expect(onPresetChange).toHaveBeenCalledWith('1m')
  })

  it('should highlight active preset', () => {
    render(<CollapsibleDateControl {...defaultProps} activePreset="1m" />)

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /Unlock Date/i }))

    const activeButton = screen.getByRole('button', { name: '1 Month' })
    expect(activeButton).toHaveClass('active')
  })

  it('should show custom date inputs when custom preset is active', () => {
    render(<CollapsibleDateControl {...defaultProps} activePreset="custom" />)

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /Unlock Date/i }))

    expect(screen.getByLabelText('Date')).toBeInTheDocument()
    expect(screen.getByLabelText('Time')).toBeInTheDocument()
  })

  it('should not show custom inputs when other preset is active', () => {
    render(<CollapsibleDateControl {...defaultProps} activePreset="1w" />)

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /Unlock Date/i }))

    expect(screen.queryByLabelText('Date')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Time')).not.toBeInTheDocument()
  })

  it('should call onCustomDateChange when custom date input changes', () => {
    const onCustomDateChange = vi.fn()
    render(
      <CollapsibleDateControl
        {...defaultProps}
        activePreset="custom"
        onCustomDateChange={onCustomDateChange}
      />,
    )

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /Unlock Date/i }))

    const dateInput = screen.getByLabelText('Date')
    fireEvent.change(dateInput, { target: { value: '2025-06-15' } })

    expect(onCustomDateChange).toHaveBeenCalledWith('2025-06-15')
  })

  it('should call onCustomTimeChange when custom time input changes', () => {
    const onCustomTimeChange = vi.fn()
    render(
      <CollapsibleDateControl
        {...defaultProps}
        activePreset="custom"
        onCustomTimeChange={onCustomTimeChange}
      />,
    )

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /Unlock Date/i }))

    const timeInput = screen.getByLabelText('Time')
    fireEvent.change(timeInput, { target: { value: '14:30' } })

    expect(onCustomTimeChange).toHaveBeenCalledWith('14:30')
  })

  it('should collapse when Escape key is pressed', () => {
    render(<CollapsibleDateControl {...defaultProps} />)

    const header = screen.getByRole('button', { name: /Unlock Date/i })

    // Expand
    fireEvent.click(header)
    expect(header).toHaveAttribute('aria-expanded', 'true')

    // Press Escape
    fireEvent.keyDown(header, { key: 'Escape' })
    expect(header).toHaveAttribute('aria-expanded', 'false')
  })

  it('should display custom hint when provided and custom preset active with no date', () => {
    render(
      <CollapsibleDateControl
        {...defaultProps}
        activePreset="custom"
        customHint="Please select a date"
      />,
    )

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /Unlock Date/i }))

    expect(screen.getByText('Please select a date')).toBeInTheDocument()
  })

  it('should not display hint when custom date is provided', () => {
    render(
      <CollapsibleDateControl
        {...defaultProps}
        activePreset="custom"
        customDate="2025-06-15"
        customHint="Please select a date"
      />,
    )

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /Unlock Date/i }))

    expect(screen.queryByText('Please select a date')).not.toBeInTheDocument()
  })

  it('should respect minDate for custom date input', () => {
    render(<CollapsibleDateControl {...defaultProps} activePreset="custom" minDate="2025-01-01" />)

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /Unlock Date/i }))

    const dateInput = screen.getByLabelText('Date') as HTMLInputElement
    expect(dateInput.min).toBe('2025-01-01')
  })
})
