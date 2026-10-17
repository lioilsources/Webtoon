// Package upstream classifies failures of the Spark services (LLM, ComfyUI, WD14).
//
// The services run on a schedule (ComfyUI 07–13, LLM 13–07). "Unavailable"
// errors make the worker requeue the job later instead of failing it.
package upstream

import (
	"errors"
	"fmt"
	"net/http"
)

var ErrUnavailable = errors.New("upstream unavailable")

type unavailable struct {
	service string
	err     error
}

func (u *unavailable) Error() string { return fmt.Sprintf("%s unavailable: %v", u.service, u.err) }
func (u *unavailable) Unwrap() []error {
	return []error{ErrUnavailable, u.err}
}

// Unavailable wraps err so errors.Is(err, ErrUnavailable) holds.
func Unavailable(service string, err error) error {
	if err == nil {
		return nil
	}
	return &unavailable{service: service, err: err}
}

func IsUnavailable(err error) bool { return errors.Is(err, ErrUnavailable) }

// StatusUnavailable reports HTTP statuses that mean "service not there right now"
// (gateway/proxy errors, overloaded) rather than a bad request.
func StatusUnavailable(code int) bool {
	switch code {
	case http.StatusBadGateway, http.StatusServiceUnavailable, http.StatusGatewayTimeout:
		return true
	}
	return false
}
